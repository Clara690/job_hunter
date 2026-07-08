import argparse
from urllib.parse import urlparse
from collections import Counter
from loguru import logger
from sqlalchemy import create_engine, MetaData, Table, select, update, bindparam
from sqlalchemy.pool import NullPool
from scraper.config import  MYSQL_ACCOUNT, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT

engine = create_engine(
     f"mysql+pymysql://{MYSQL_ACCOUNT}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/data_jobs",
    poolclass=NullPool
)

metadata = MetaData()

# function for constructing job id from url
def extract_104_job_id(link: str) -> str | None:
    path = urlparse(link).path
    parts = [p for p in path.split('/') if p]
    return parts[-1] if parts else None

def extract_cake_job_id(link: str) -> str | None:
    if not link or '/jobs/' not in link:
        return None
    return link.rsplit('/jobs/', 1)[-1]

# backfill the table with existing data
def backfill_table(table_name: str, extractor, dry_run: bool):
    table = Table(table_name, metadata, autoload_with=engine)

    if 'source_job_id' not in table.columns:
        logger.error(
            f'{table_name} has no source_job_id column yet, alter the table first'
        )
        return
    with engine.connect() as conn:
        # only pull rows haven't been backfilled yet
        rows = conn.execute(
            select(table.c.id, table.c.link).where(
                (table.c.source_job_id == None) | (table.c.source_job_id == '')
            )
        ).fetchall()

        logger.info(f'{table_name}: {len(rows)} rows need backfilling')

        computed = [] # (id, source_job_id) pairs
        unparseable = []

        for row in rows:
            job_id = extractor(row.link)
            if job_id is None:
                unparseable.append(row.id)
                continue
            computed.append((row.id, job_id))

        if unparseable:
            logger.warning(
                f'{table_name}: could not parse a source_job_id for {len(unparseable)}'
                f'rows (ids: {unparseable[:10]}"..." if {len(unparseable)} > 10 else ''}).'
                f'These links may be malformed — inspect them manually.'
            )
        # check for collisions before writing anything
        id_counts = Counter(job_id for _, job_id in computed)
        duplicates = {job_id: count for job_id, count in id_counts.items() if count > 1}

        if duplicates:
            logger.warning(
                f'{table_name}: found {len(duplicates)} duplictaed source_job_id values'
            )
        if dry_run:
            logger.info(
                f'{table_name}: dry run - would update {len(computed)} rows'
                f'o rows written'
            )
            return 
        if computed:
            conn.execute(
                update(table).where(table.c.id == bindparam("_id")),
                [{"_id": row_id, "source_job_id": job_id} for row_id, job_id in computed],
            )
            conn.commit()
            logger.info(f"{table_name}: updated {len(computed)} rows")

            

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--dry-run',
        action = 'store_true',
        help = 'Preview what would change without writing to the database',        
    )
    args = parser.parse_args()

    backfill_table('jobs_104',  extract_104_job_id, args.dry_run)
    backfill_table("jobs_cake", extract_cake_job_id, args.dry_run)


if __name__ == '__main__':
    main()

