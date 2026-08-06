import argparse, sys
from loguru import logger
from scraper.tasks_104_scraper import air_scrape_104_jobs_upload_mysql

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--search-term', required=True)
    parser.add_argument('--page', type=int, required=True)
    args = parser.parse_args()
    try:
        air_scrape_104_jobs_upload_mysql(args.search_term, args.page)
    except Exception:
        logger.exception(f'104 scrape failed: term={args.search_term!r}, page={args.page}')
        sys.exit(1)

if __name__ == '__main__':
    main()