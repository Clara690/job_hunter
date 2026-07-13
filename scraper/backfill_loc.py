import re
import argparse
from loguru import logger
from collections import Counter
from sqlalchemy import create_engine, MetaData, Table, select, update, bindparam
from sqlalchemy.pool import NullPool
from scraper.config import  MYSQL_ACCOUNT, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT

# database connection
engine = create_engine(
    f"mysql+pymysql://{MYSQL_ACCOUNT}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/data_jobs",
    poolclass=NullPool
)

metadata = MetaData()

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
    "lienchiang county": ("連江縣", "Lienchiang County"),
}

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

def backfill_loc(table_name: str, extractor, dry_run: bool):
    table = Table(table_name, metadata, autoload_with=engine)

    with engine.connect() as conn:
        # only pull rows haven't been backfilled yet
        rows = conn.execute(
            select(table.c.id, table.c.location).where((table.c.city_zh == None) & (table.c.city_en == None))
        ).fetchall()

        logger.info(f'{table_name}: {len(rows)} rows need backfilling')

        computed = []
        unparseable = []

        for row in rows:
            loc_data = extractor(row.location)
            city_zh = loc_data.get('city_zh')
            city_en = loc_data.get('city_en')
            is_overseas = loc_data.get('is_overseas')

            if city_zh is None or city_en is None:
                unparseable.append(row.id)
                continue
            
            computed.append((row.id, city_zh, city_en, is_overseas))
        
        if unparseable:
            logger.warning(
                f'Failed to convert location information for {len(unparseable)} rows'
            )
        
        # check for collisions 
        id_counts = Counter(id for id, _, _, _ in computed)
        duplicates = {id: count for id, count in id_counts.items() if count > 1}

        if duplicates: 
            logger.warning(
                f'{table_name}: found {len(duplicates)} duplicated ids'
            )
        
        if dry_run:
            logger.info(
                f'{table_name}: dry run - would update {len(computed)} rows. 0 rows written'
            )
            return
        
        if computed:
            conn.execute(
                update(table).where(table.c.id == bindparam('_id')),
                [{'_id': id, 'city_zh': city_zh, 'city_en': city_en, 'is_overseas': is_overseas} for id, city_zh, city_en, is_overseas in computed],
            )
            conn.commit()
            logger.info(f'{table_name}: updated {len(computed)} rows')
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--dry-run',
        action= 'store_true',
        help='Preview what would change without writing to the database',
    )
    args = parser.parse_args()

    backfill_loc('job_location_cake', parse_cake_location, args.dry_run)


if __name__ == '__main__':
    main()