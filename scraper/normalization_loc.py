from sqlalchemy import (create_engine, MetaData, Table, Column, Integer,
                        String, Boolean, insert, select)
from sqlalchemy.pool import NullPool
from scraper.config import  MYSQL_ACCOUNT, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT
from loguru import logger
import re 

# create the connection to MySQL database
engine = create_engine(
    f"mysql+pymysql://{MYSQL_ACCOUNT}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/data_jobs",
    poolclass=NullPool
)
# define the table 
metadata = MetaData()

# define table schema
cities_table = Table(
    'cities', 
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('city_zh', String(10), nullable=False, unique=True),
    Column('city_en', String(30), nullable=False, unique=True),
    Column('is_overseas', Boolean, nullable=False, default=False)
)

# create table if not exist 
metadata.create_all(engine)

# mapping of Taiwanese cities (en <--> zh)
TAIWAN_CITY_MAP = {
    "taipei": ("台北市", "Taipei City"), "taipei city": ("台北市", "Taipei City"),
    "new taipei": ("新北市", "New Taipei City"), "new taipei city": ("新北市", "New Taipei City"),
    "taoyuan": ("桃園市", "Taoyuan City"), "taoyuan city": ("桃園市", "Taoyuan City"),
    "taichung": ("台中市", "Taichung City"), "taichung city": ("台中市", "Taichung City"),
    "tainan": ("台南市", "Tainan City"), "tainan city": ("台南市", "Tainan City"),
    "kaohsiung": ("高雄市", "Kaohsiung City"), "kaohsiung city": ("高雄市", "Kaohsiung City"),
    "keelung city": ("基隆市", "Keelung City"),
    "hsinchu city": ("新竹市", "Hsinchu City"),          
    "hsinchu county": ("新竹縣", "Hsinchu County"),
    "chiayi city": ("嘉義市", "Chiayi City"),             
    "chiayi county": ("嘉義縣", "Chiayi County"),
    "miaoli county": ("苗栗縣", "Miaoli County"),
    "changhua county": ("彰化縣", "Changhua County"),
    "nantou county": ("南投縣", "Nantou County"),
    "yunlin county": ("雲林縣", "Yunlin County"),
    "pingtung county": ("屏東縣", "Pingtung County"),
    "yilan county": ("宜蘭縣", "Yilan County"),
    "hualien county": ("花蓮縣", "Hualien County"),
    "taitung county": ("台東縣", "Taitung County"),
    "penghu county": ("澎湖縣", "Penghu County"),
    "kinmen county": ("金門縣", "Kinmen County"),
    "lienchiang county": ("連江縣", "Lienchiang County")
}

# load the table
cities_table = Table('cities', metadata, autoload_with=engine)


# load the city id from `cities` table in the DB
def load_city_ids(engine, cities_table) -> dict:
    with engine.connect() as conn:
        rows = conn.execute(select(cities_table.c.city_zh, cities_table.c.id)).fetchall()
        return {row.city_zh: row.id for row in rows}

# a function for mapping location information for cake
def parse_cake_location(raw: str) -> dict:
    if not raw:
        return {'city_zh': None, 'city_en': None, 'is_overseas': None}
    
    if 'taiwan' not in raw.lower():
        return {'city_zh': '海外', 'city_en': 'Overseas', 'is_overseas': True}
    
    segments = [s.strip() for s in raw.split(',')]
    for seg in reversed(segments):
        seg_clean = re.sub(r'\d+', '', seg).strip().lower() # drop zip codes
        if seg_clean == 'taiwan':
            continue
        if seg_clean in TAIWAN_CITY_MAP:
            city_zh, city_en = TAIWAN_CITY_MAP[seg_clean]
            return {'city_zh': city_zh, 'city_en': city_en, 'is_overseas': False}
        
    return {'city_zh': None, 'city_en': None, 'is_overseas': False}


if __name__ == '__main__':
    seen = set()
    rows = [{'city_zh': '海外', 'city_en': 'Overseas', 'is_overseas': True}]

    # insert the data in to `cities` table
    for city_zh, city_en in TAIWAN_CITY_MAP.values():
        if city_zh not in seen:
            rows.append({'city_zh': city_zh, 'city_en': city_en, 'is_overseas': False})
            seen.add(city_zh)

    with engine.connect() as conn:
        conn.execute(insert(cities_table), rows)
        conn.commit()
    logger.info('Successfully created the see table')

