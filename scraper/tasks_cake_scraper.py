from scraper.worker import app
import requests
import urllib.parse
from bs4 import BeautifulSoup
import re 
import json
from datetime import datetime
import time, random
import uuid
import pandas as pd
from loguru import logger 
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import insert
from sqlalchemy import select
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import OperationalError
from sqlalchemy import (MetaData, Table, Column, Integer, String, DateTime, Text, 
                        TIMESTAMP, UniqueConstraint, ForeignKey, text)
from scraper.config import MYSQL_ACCOUNT, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT
        

# CAKE_JOB_URL = 'https://www.cake.me/jobs'
API_URL = 'https://api.cake.me/api/client/v1/jobs/search'


# create the connection to MySQL database
engine = create_engine(
    f'mysql+pymysql://{MYSQL_ACCOUNT}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/data_jobs',
    poolclass=NullPool
)
# define the table 
metadata = MetaData()

# the main table 
# location information is stored in another table as some roles are associated with more than one location
jobs_table = Table(
     'jobs_cake', 
     metadata,
     Column('id', Integer, primary_key=True, autoincrement=True),
     Column('source_job_id', String(100), nullable=False, unique=True),
     Column('job_name', String(100), nullable=False),
     Column('company', String(100), nullable=False),
     Column('job_type', String(50), nullable=True),  
     Column('experience', Integer, nullable=True),
     Column('manage_resp', String(50), nullable=True),
     Column('seniority', String(50), nullable=True),
     Column('remote', String(10), nullable=True),
     Column('salary_min', Integer, nullable=True),
     Column('salary_max', Integer, nullable=True),
     Column('salary_crcy', String(5), nullable=True), # currency
     Column('salary_type', String(50), nullable=True),
     Column('popularity', Integer, nullable=True),
     Column('link', Text, nullable=False),
     Column('last_updated', DateTime(6), nullable=True),
     Column('inserted_at', TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'), nullable=False),
    
#     # unique key to prevent duplicated job postings
    UniqueConstraint('source_job_id', name='uix_source_job_id')
)
# the bridge table 
job_location_table = Table(
    'job_location_cake',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('job_id', Integer, ForeignKey('jobs_cake.id', ondelete='CASCADE'), nullable=False),
    Column('location', String(100), nullable=False),    
    
    # unique key to prevent duplicate locations for the same job
    UniqueConstraint('job_id', 'location', name='uix_job_id_location')
)

# create table if not exist 
metadata.create_all(engine)


# the main function to scrape job listings from Cake's job board based on the search term
# @app.task()
def scrape_cake_jobs(search_term, page):
    # headers
    HEADERS = {
        'sec-ch-ua-platform': '"Windows"',
        'Referer': 'https://www.cake.me/',
        'sec-ch-ua': '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'content-type': 'application/json',
        'X-Search-Session-Id': str(uuid.uuid4()),
    }


    # add other search parameter
    json_data = {
        'query': search_term,
        'filters': {},
        'sort_by': 'popularity',
        'page': page,
        'per_page': 10,
    }
    # network level failure
    try:
        response = requests.post(API_URL, json=json_data, headers=HEADERS, timeout=10)
        # soup = BeautifulSoup(response.content, 'html.parser')
    except requests.exceptions.RequestException:
        logger.exception(f'Network error while scraping cake, page {page}, term "{search_term}".')
        raise
    
    if  response.status_code != 200:
        logger.warning(f'Status code {response.status_code} for page {page}, term "{search_term}".')
        return None
    
    # parsing level failure 
    try: 
        data = response.json()
        # the raw data of job postings
        all_jobs = data['data']
    except (KeyError, ValueError):
        logger.exception(f'Unexpected response shape from cake on page {page}, term "{search_term}".')
        return None


    # for storing the results
    cleaned_jobs = []

    for job in all_jobs:
        try:
            #location information, since it's nested so needed to be processed separately
            locales = job.get('locations_with_locale', [])

            # extract all 'en' values and ignore any missing ones
            english_locations = [loc.get('en') for loc in locales if loc.get('en')]

            # some basic preprocessing to prevent the function from crashing

            title = job.get('title')
            company_name = job.get('page', {}).get('name')
            if title is None or company_name is None:
                logger.warning(f"Skipping job with missing title/ company: {job.get('path')}")
                continue
            salary_min = job.get('salary', {}).get('min')
            salary_max = job.get('salary', {}).get('max')

            # new dictionary with only the desired keys
            filtered_job = {            
                'source_job_id':job.get('path'),
                'job_name': title[:100] if len(title) > 100 else title,
                'company': company_name[:100] if len(company_name) > 100 else company_name,
                'raw_locations': english_locations,
                'job_type': job.get('job_type'),
                'experience': job.get('min_work_exp_year'),
                'manage_resp': job.get('number_of_management'),
                'seniority':job.get('seniority_level'),
                'remote': None,
                'salary_min': int(float(salary_min)) if salary_min else None,
                'salary_max': int(float(salary_max)) if salary_max else None,
                'salary_crcy': job.get('salary', {}).get('currency'),
                'salary_type':job.get('salary', {}).get('type'),
                'popularity': job.get('unique_impressions_count'),
                'last_updated': datetime.fromisoformat(job.get('content_updated_at').replace('Z', '+00:00')),
                # construct the relative path 
                'link': job.get('page', {}).get('path')+ '/jobs/' + job.get('path')
            }
            cleaned_jobs.append(filtered_job)
        except KeyError as e:
            logger.warning(f'Skipping one malformed job listing (missing key {e}) on page {page}')
            continue
    if not all_jobs:
        return None
    time.sleep(random.uniform(1.5, 3.5))
    return cleaned_jobs


# upload the data to MySQL 
@app.task(bind=True, autoretry_for=(OperationalError,), 
    retry_backoff=True, # waits between retries,
    max_retries=3)
def scrape_cake_jobs_upload_mysql(self, search_term, page):

    # the data scrpae from cake 
    records = scrape_cake_jobs(search_term, page)


    if not records:
        logger.warning(f'No data found on page {page}.')
        return 'No data'

    with engine.connect() as conn:
    # prepare the data 
        jobs_to_insert = []
        location_map = {} # Maps a unique key to its location 
        
        for record in records:
            # extract locations and remove from the main dict
            locs = record.pop('raw_locations', [])
            jobs_to_insert.append(record)

            # create a composite key to track this job
            unique_key = (record['job_name'], record['company'])
            location_map[unique_key] = locs
        # insert all jobs 
        insert_stmt = insert(jobs_table).values(jobs_to_insert)
        on_duplicate_stmt = insert_stmt.on_duplicate_key_update(
            salary_min = insert_stmt.inserted.salary_min,
            salary_max = insert_stmt.inserted.salary_max
        )
        conn.execute(on_duplicate_stmt)

        # fetch the corresponding ids in the main table 
        job_name = [j['job_name'] for j in jobs_to_insert]
        companies = [j['company'] for j in jobs_to_insert]

        fetch_stmt = select(jobs_table.c.id, jobs_table.c.job_name, jobs_table.c.company).where(
            jobs_table.c.job_name.in_(job_name),
            jobs_table.c.company.in_(companies)
        )
        db_jobs = conn.execute(fetch_stmt).fetchall()

        # insert location info to the location table
        locations_to_insert = []
        for db_job in db_jobs:
            job_id = db_job.id
            unique_key = (db_job.job_name, db_job.company)
            
            # match the DB id back to the locations 
            if unique_key in location_map:
                for loc in location_map[unique_key]:
                    locations_to_insert.append({
                        'job_id': job_id,
                        'location': loc
                    })
        if locations_to_insert:
            loc_insert_stmt = insert(job_location_table).values(locations_to_insert)
            # use insert ignore to prevent duplicate location rows
            loc_on_duplicate = loc_insert_stmt.on_duplicate_key_update(
                job_id = loc_insert_stmt.inserted.job_id
            )
            conn.execute(loc_on_duplicate)
        conn.commit()

    logger.info(f'Successfully uploaded {len(records)} jobs to MySQL for page {page}')
    return f'Success: Page {page}'

