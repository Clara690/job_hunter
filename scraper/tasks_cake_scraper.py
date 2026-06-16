from scraper.worker import app
import requests
import urllib.parse
from bs4 import BeautifulSoup
import re 
import json
from datetime import datetime
import pandas as pd
from loguru import logger 
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.pool import NullPool
from sqlalchemy import MetaData, Table, Column, Integer, String, DateTime, Text, TIMESTAMP, UniqueConstraint, text
from scraper.config import MYSQL_ACCOUNT, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT
        

# CAKE_JOB_URL = "https://www.cake.me/jobs"
API_URL = "https://api.cake.me/api/client/v1/jobs/search"
# DEFAULT_HEADERS = {
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
# }
HEADERS = {
    'sec-ch-ua-platform': '"Windows"',
    'Referer': 'https://www.cake.me/',
    'sec-ch-ua': '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'content-type': 'application/json',
    'X-Search-Session-Id': '83f5fcf0-19ee-40e9-b390-17dc78c0ae92',
}

# create the connection to MySQL database
engine = create_engine(
    f"mysql+pymysql://{MYSQL_ACCOUNT}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/data_jobs",
    poolclass=NullPool
)
# define the table 
metadata = MetaData()

jobs_table = Table(
     "jobs_cake", 
     metadata,
     Column("id", Integer, primary_key=True, autoincrement=True),
     Column("job_name", String(100), nullable=False),
     Column("company", String(50), nullable=False),
     Column("location", String(255), nullable=False),
     Column("job_type", String(50), nullable=True),  
     Column("experience", String(50), nullable=True),
     Column("manage_resp", String(50), nullable=True),
     Column("seniority", String(50), nullable=True),
     Column("remote", String(10), nullable=True),
     Column("salary_min", String(50), nullable=True),
     Column("salary_max", String(50), nullable=True),
     Column("salary_crcy", String(50), nullable=True),
     Column("salary_type", String(50), nullable=True),
     Column("popularity", Integer, nullable=True),
     Column("link", Text, nullable=False),
     Column("last_updated", DateTime(6), nullable=True),
     Column("inserted_at", TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), nullable=False),
    
#     # unique key to prevent duplicated job postings
    UniqueConstraint("job_name", "company", "location", name="uix_job_company_location")
)

# create table if not exist 
metadata.create_all(engine)


# the main function to scrape job listings from Cake's job board based on the search term
# @app.task()
def scrape_cake_jobs(search_terms, page):


    # add other search parameter
    json_data = {
        'query': search_terms,
        'filters': {},
        'sort_by': 'popularity',
        'page': page,
        'per_page': 10,
    }
    try:
        response = requests.post(API_URL, json=json_data, headers=HEADERS, timeout=10)
        print(response.url)
        if  response.status_code != 200:
            print(f"Failed to access the website. Status code: {response.status_code}")

            return None
        # soup = BeautifulSoup(response.content, "html.parser")
    except requests.exceptions.RequestException as e:
        print(f"Network error occurred:{e}")
        return None
    
    # the raw data of job postings
    data = response.json()
    all_jobs = data['data']

    # for storing the results
    cleaned_jobs = []

    for job in all_jobs:
        #location information, since it's nested so needed to be processed separately
        locales = job.get('locations_with_locale', [])

        # extract all 'en' values and ignore any missing ones
        english_locations = [loc.get('en') for loc in locales if loc.get('en')]
        
        # join the locations into one string
        joined_locations = '|'.join(english_locations) if english_locations else None

        # new dictionary with only the desired keys
        filtered_job = {            
            'job_name': job.get('title'),
            'company': job.get('page', {}).get('name'),
            'location': joined_locations,
            'job_type': job.get('job_type'),
            'experience': job.get('min_work_exp_year'),
            'manage_resp': job.get('number_of_management'),
            'seniority':job.get('seniority_level'),
            'remote': None,
            'salary_min': job.get('salary', {}).get('min'),
            'salary_max': job.get('salary', {}).get('max'),
            'salary_crcy': job.get('salary', {}).get('currency'),
            'salary_type':job.get('salary', {}).get('type'),
            'popularity': job.get('unique_impressions_count'),
            'last_updated': datetime.fromisoformat(job.get('content_updated_at').replace('Z', '+00:00')),
            # construct the relative path 
            'link': job.get('page', {}).get('path')+ '/jobs/' + job.get('path')
        }
        cleaned_jobs.append(filtered_job)
    return cleaned_jobs


# upload the data to MySQL 
@app.task(bind=True, max_retries=3)
def scrape_cake_jobs_upload_mysql(self, search_term, page):

    # the data scrpae from cake 
    records = scrape_cake_jobs(search_term, page)

    if not records:
        logger.warning(f'No data found on page {page}.')
        return 'No data'

    with engine.connect() as conn:
        # create an insert statement
        insert_stmt = insert(jobs_table).values(records)

        # add 'ON DUPLICATE KEY UPDATE' logic
        on_duplicate_stmt = insert_stmt.on_duplicate_key_update(
            salary_min = insert_stmt.inserted.salary_min,
            salary_max = insert_stmt.inserted.salary_max

        )
        # execute the insert statement
        conn.execute(on_duplicate_stmt)
        conn.commit() # commit the transaction after each insert 
    logger.info(f'Successfully uploaded {len(records)} jobs to MySQL for page {page}')
    return f"Success: Page {page}"

