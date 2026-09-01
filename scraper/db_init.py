from loguru import logger
from sqlalchemy import ForeignKey, create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import OperationalError
from sqlalchemy import (MetaData, Table, Column, Integer, Numeric, ForeignKeyConstraint,
                        String, CHAR, Text, TIMESTAMP, UniqueConstraint, text, DateTime)
from scraper.config import MYSQL_ACCOUNT, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT

# create the connection to MySQL database
engine = create_engine(
    f"mysql+pymysql://{MYSQL_ACCOUNT}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/data_jobs",
    poolclass=NullPool
)
# define the tables
metadata = MetaData()

# cities 
cities_table = Table(
    "cities",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("city_zh", String(10), nullable=False, unique=True),
    Column("city_en", String(30), nullable=False, unique=True),
    Column("is_overseas", Integer, nullable=False),  # tinyint(1)
)

jobs_104_table = Table(
    "jobs_104", 
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("source_job_id", String(50), nullable=False, unique=True),
    Column("job_name", String(255), nullable=False),
    Column("company", String(50), nullable=False),
    Column("raw_location", String(50), nullable=False),
    Column("city", String(50),nullable=True),
    Column("district", String(50), nullable=True),
    Column("city_id", Integer, nullable=True),
    Column("experience", Integer, nullable=False),
    Column("remote", CHAR(3), nullable=False),
    Column("salary_min", Integer, nullable=False),
    Column("salary_max", Integer, nullable=False),
    Column('salary_min_monthly_twd', Numeric(12, 2), nullable=True), 
    Column('salary_max_monthly_twd', Numeric(12, 2), nullable=True),
    Column("period", Integer, nullable=True),      
    Column("job_type", Integer, nullable=True),
    Column("salary_confidence", String(20), nullable=True),
    Column("link", Text, nullable=False),
    Column("inserted_at", TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), nullable=False),
    
    # unique key to prevent duplicated job postings
    UniqueConstraint("source_job_id", name="uix_source_job_id"),
    ForeignKeyConstraint(['city_id'], ['cities.id'], name='fk_jobs_104_city'),
    # UniqueConstraint("job_name", "company", "raw_location", name="uix_job_company_location")
)

# create table if not exist 
metadata.create_all(engine)

logger.info("Table jobs_104 created or already exists.")

# the main table 
# location information is stored in another table as some roles are associated with more than one location
jobs_cake_table = Table(
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
     Column('salary_min_monthly_twd', Numeric(12, 2), nullable=True), 
     Column('salary_max_monthly_twd', Numeric(12, 2), nullable=True),
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
    Column('city_id', Integer, nullable=True),
    
    # unique key to prevent duplicate locations for the same job
    UniqueConstraint('job_id', 'location', name='uix_job_id_location'),
    ForeignKeyConstraint(['city_id'], ['cities.id'], name='fk_job_location_cake_city'),
)

# create table if not exist 
metadata.create_all(engine)
from loguru import logger
from sqlalchemy import ForeignKey, create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import OperationalError
from sqlalchemy import (MetaData, Table, Column, Integer, Numeric, ForeignKeyConstraint,
                        String, CHAR, Text, TIMESTAMP, UniqueConstraint, text, DateTime)
from scraper.config import MYSQL_ACCOUNT, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT

# create the connection to MySQL database
engine = create_engine(
    f"mysql+pymysql://{MYSQL_ACCOUNT}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/data_jobs",
    poolclass=NullPool
)
# define the tables
metadata = MetaData()

# cities 
cities_table = Table(
    "cities",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("city_zh", String(10), nullable=False, unique=True),
    Column("city_en", String(30), nullable=False, unique=True),
    Column("is_overseas", Integer, nullable=False),  # tinyint(1)
)

jobs_104_table = Table(
    "jobs_104", 
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("source_job_id", String(50), nullable=False, unique=True),
    Column("job_name", String(255), nullable=False),
    Column("company", String(50), nullable=False),
    Column("raw_location", String(50), nullable=False),
    Column("city", String(50),nullable=True),
    Column("district", String(50), nullable=True),
    Column("city_id", Integer, nullable=True),
    Column("experience", Integer, nullable=False),
    Column("remote", CHAR(3), nullable=False),
    Column("salary_min", Integer, nullable=False),
    Column("salary_max", Integer, nullable=False),
    Column('salary_min_monthly_twd', Numeric(12, 2), nullable=True), 
    Column('salary_max_monthly_twd', Numeric(12, 2), nullable=True),
    Column("period", Integer, nullable=True),      
    Column("job_type", Integer, nullable=True),
    Column("salary_confidence", String(20), nullable=True),
    Column("link", Text, nullable=False),
    Column("inserted_at", TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), nullable=False),
    
    # unique key to prevent duplicated job postings
    UniqueConstraint("source_job_id", name="uix_source_job_id"),
    ForeignKeyConstraint(['city_id'], ['cities.id'], name='fk_jobs_104_city'),
    # UniqueConstraint("job_name", "company", "raw_location", name="uix_job_company_location")
)

# create table if not exist 
metadata.create_all(engine)

logger.info("Table jobs_104 created or already exists.")

# the main table 
# location information is stored in another table as some roles are associated with more than one location
jobs_cake_table = Table(
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
     Column('salary_min_monthly_twd', Numeric(12, 2), nullable=True), 
     Column('salary_max_monthly_twd', Numeric(12, 2), nullable=True),
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
    Column('city_id', Integer, nullable=True),
    
    # unique key to prevent duplicate locations for the same job
    UniqueConstraint('job_id', 'location', name='uix_job_id_location'),
    ForeignKeyConstraint(['city_id'], ['cities.id'], name='fk_job_location_cake_city'),
)

# create table if not exist 
metadata.create_all(engine)