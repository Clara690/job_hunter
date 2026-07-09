from scraper.worker import app
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import time, random
import pandas as pd
import numpy as np
from loguru import logger 
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import OperationalError
from sqlalchemy import MetaData, Table, Column, Integer, String, CHAR, Text, TIMESTAMP, UniqueConstraint, text
from scraper.config import MYSQL_ACCOUNT, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT
from scraper.backfill import extract_104_job_id
# create the connection to MySQL database
engine = create_engine(
    f"mysql+pymysql://{MYSQL_ACCOUNT}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/data_jobs",
    poolclass=NullPool
)
# define the table 
metadata = MetaData()

jobs_table = Table(
    "jobs_104", 
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("source_job_id", String(50), nullable=False, unique=True),
    Column("job_name", String(255), nullable=False),
    Column("company", String(50), nullable=False),
    Column("raw_location", String(50), nullable=False),
    Column("city", String(50),nullable=True),
    Column("district", String(50), nullable=True),
    Column("experience", Integer, nullable=False),
    Column("remote", CHAR(3), nullable=False),
    Column("salary_min", Integer, nullable=False),
    Column("salary_max", Integer, nullable=False),
    Column("period", Integer, nullable=True),      
    Column("job_type", Integer, nullable=True),
    Column("salary_confidence", String(20), nullable=True),
    Column("link", Text, nullable=False),
    Column("inserted_at", TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), nullable=False),
    
    # unique key to prevent duplicated job postings
    UniqueConstraint("source_job_id", name="uix_source_job_id")
    # UniqueConstraint("job_name", "company", "raw_location", name="uix_job_company_location")
)

# create table if not exist 
metadata.create_all(engine)

# a function for classifying salary type as it does not exisit in the raw data
MONTHLY_SALARY_FLOOR = 29000 # minimum wage in TW in 2026
def classify_salary_confidence(salary_min: int, salary_max: int) -> str:
    if not salary_min and not salary_max:
        return 'unspecified'
    # if the either of the salary range does not fall in the valid range
    if (salary_min and salary_min < MONTHLY_SALARY_FLOOR) or (salary_max and salary_max < MONTHLY_SALARY_FLOOR):
        return 'non_monthly'
    return 'monthly'

# the scrape function for 104 jobs, takes in the search term and the page number as parameters
def scrape_104_jobs(search_term, page):
    based_url = "https://www.104.com.tw/jobs/search/api/jobs"

    # define the parameters for the GET request
    params = {
        "asc": 1,
        "jobsource": "joblist_search",
        "keyword": search_term,
        "mode": "s",
        "order": 4,
        "page": page,  # Inject the current page number
        "pagesize": 20,
        "searchJobs": 1,
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "Referer": "https://www.104.com.tw/jobs/search/",
    }
    # for storing the results
    jobs = []
    # the acutal scraping process
    # network level failure
    try:
        response = requests.get(based_url, params=params, headers=headers)
        
    except requests.exceptions.RequestException:
        logger.exception(f'Network error while scraping 104, page {page}, term "{search_term}".')
        # let Celery retry automatically
        raise
    if response.status_code != 200:
        logger.warning(f'Status code {response.status_code} for page {page}, term "{search_term}".')
        return None
    # parsing level failure -> change in the response 
    try:
        data = response.json()['data']
    except (KeyError, ValueError):
        logger.exception(f'Unexpected response shape from 104 on page {page}, term "{search_term}".')
        return None
    jobs = []
    for job in data:
        try:
            raw_loc = job["jobAddrNoDesc"]
            description = {
                "source_job_id": extract_104_job_id(job['link']['job']),
                "job_name": job["jobName"],
                "company": job["custName"],
                "raw_location": raw_loc,
                "city":raw_loc[:3] if raw_loc[:3] else None,
                "district":raw_loc[3:] if raw_loc[3:] else None,
                "experience": job["jobRo"],
                "remote": job["remoteWorkType"],
                "salary_min": job["salaryLow"],
                "salary_max": job["salaryHigh"],
                "period": job.get("period"),        
                "job_type": job.get("jobType"), 
                "salary_confidence": classify_salary_confidence(job['salaryLow'], job['salaryHigh']),
                "link": job["link"]["job"],
            }
            jobs.append(description)
        except KeyError as e:
            logger.warning(f'Skipping one malformed job listing (missing key {e}) on page {page}')
            continue
    if not jobs:
        return None
    
    df = pd.DataFrame(jobs)
    df = df.replace({np.nan: None})
    time.sleep(random.uniform(1.5, 3.5))
    return df



    
# upload to MySQL in one task
@app.task(bind=True, autoretry_for=(OperationalError,), 
    retry_backoff=True, # waits between retries,
    max_retries=3)
def scrape_104_jobs_upload_mysql(self, search_term, page):
    
    # the data scraped from the website
    df = scrape_104_jobs(search_term, page)

    if df is None or df.empty:
        logger.warning(f'No data found on page {page}.')
        return 'No data'
    
    # convert the data frame to a list of dict for bulk insert
    records = df.to_dict(orient="records")

    with engine.connect() as conn:
        # create an insert statement
        insert_stmt = insert(jobs_table).values(records)

        # add 'ON DUPLICATE KEY UPDATE' logic
        on_duplicate_stmt = insert_stmt.on_duplicate_key_update(
            salary_min=insert_stmt.inserted.salary_min,
            salary_max=insert_stmt.inserted.salary_max,
            period=insert_stmt.inserted.period,
            job_type=insert_stmt.inserted.job_type,
            salary_confidence=insert_stmt.inserted.salary_confidence
        )
        # execute the insert statement
        conn.execute(on_duplicate_stmt)
        conn.commit()  # commit the transaction after each insert
    logger.info(f'Successfully uploaded {len(df)} jobs to MySQL for page {page}') 
    return f"Success: Page {page}"
