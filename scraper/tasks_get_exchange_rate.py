from scraper.worker import app
import requests
from loguru import logger
from sqlalchemy import (create_engine, MetaData, Table, Column, String, Numeric, text, TIMESTAMP)
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.pool import NullPool
from scraper.config import MYSQL_ACCOUNT, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT

# connection to MySQL database
engine = create_engine(
    f"mysql+pymysql://{MYSQL_ACCOUNT}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/data_jobs",
    poolclass=NullPool,
)

# define the table
metadata = MetaData()

# the exchange rate table, create the table if not exist
ex_rate_table = Table(
    'exchange_rates',
    metadata,
    Column('currency', String(3), primary_key=True),
    Column('rate_to_twd', Numeric(12, 6), nullable=False),
    Column(
        'updated_at',
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    ),
)

# create the table if not exist
metadata.create_all(engine)

# the list of currency to look for 
CURRENCY_OF_INTEREST = {"USD", "TWD", "VND", "JPY", "IDR", 
                        "SGD", "EUR", "HKD", "MYR", "CAD", "THB"}

# the exchange rate api source
RATES_URL = "https://open.er-api.com/v6/latest/TWD"

@app.task(bind=True, autoretry_for=(requests.exceptions.RequestException,), retry_backoff=True, max_retries=3)
def refresh_exchange_rates(self):
    resp = requests.get(RATES_URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get('result') != 'success':
        logger.error(f'Exchange rate API returned non-success: {data}')
        return 'Failed'
    
    twd_rates = data['rates']

    rows = []
    for currency in CURRENCY_OF_INTEREST:
        if currency == 'TWD':
            rows.append({'currency': currency, 'rate_to_twd': 1.0})
            continue
        rate_from_twd = twd_rates.get(currency)
        if not rate_from_twd:
            logger.warning(f'No rate for {currency}, skipping...')
            continue
        rows.append({'currency': currency, 'rate_to_twd': 1 / rate_from_twd})

    with engine.connect() as conn:
        stmt = insert(Table('exchange_rates', metadata, autoload_with=engine)).values(rows)
        stmt = stmt.on_duplicate_key_update(rate_to_twd=stmt.inserted.rate_to_twd)
        
        conn.execute(stmt)
        conn.commit()

        logger.info(f'Refreshed exchange rates for {len(rows)} currencies')
        return f'Success: {len(rows)} currencies'