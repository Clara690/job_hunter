from loguru import logger
import sys
from scraper.tasks_get_exchange_rate import air_refresh_exchange_rates

def main():
    try:
        air_refresh_exchange_rates()
    except Exception:
        logger.exception('Exchange rate refresh failed')
        sys.exit(1)

if __name__ == '__main__':
    main()