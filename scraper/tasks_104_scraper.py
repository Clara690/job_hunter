from scraper.worker import app
import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
from loguru import logger 
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import OperationalError
from sqlalchemy import MetaData, Table, Column, Integer, String, CHAR, Text, TIMESTAMP, UniqueConstraint, text
from scraper.config import MYSQL_ACCOUNT, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT
        
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
    Column("job_name", String(255), nullable=False),
    Column("company", String(50), nullable=False),
    Column("location", String(50), nullable=False),
    Column("experience", Integer, nullable=False),
    Column("remote", CHAR(3), nullable=False),
    Column("salary_low", Integer, nullable=False),
    Column("salary_high", Integer, nullable=False),
    Column("link", Text, nullable=False),
    Column("inserted_at", TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), nullable=False),
    
    # unique key to prevent duplicated job postings
    UniqueConstraint("job_name", "company", "location", name="uix_job_company_location")
)

# create table if not exist 
metadata.create_all(engine)

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
    try:
        response = requests.get(based_url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            data = data["data"]
            for job in data:
                description = {
                    "job_name": job["jobName"],
                    "company": job["custName"],
                    "location": job["jobAddrNoDesc"],
                    "experience": job["jobRo"],
                    "remote": job["remoteWorkType"],
                    "salary_low": job["salaryLow"],
                    "salary_high": job["salaryHigh"],
                    "link": job["link"]["job"],
                }
                jobs.append(description)
            df = pd.DataFrame(jobs)
            return df
        else:
            print(f"Failed to retrieve data: {response.status_code}")
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

    
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
            salary_low=insert_stmt.inserted.salary_low,
            salary_high=insert_stmt.inserted.salary_high,
            
        )
        # execute the insert statement
        conn.execute(on_duplicate_stmt)
        conn.commit()  # commit the transaction after each insert
    logger.info(f'Successfully uploaded {len(df)} jobs to MySQL for page {page}') 
    return f"Success: Page {page}"