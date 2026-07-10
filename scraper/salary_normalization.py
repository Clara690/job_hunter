from sqlalchemy import Table, select
from loguru import logger

# approximation constant for salary convertion
HOURS_PER_MONTH = 176
DAYS_PER_MONTH = 22

# load the exchange rate table from database
def load_exchange_rate(engine, exchange_rates_table: Table) -> dict:
    with engine.connect() as conn:
        rows = conn.execute(
            select(exchange_rates_table.c.currency, exchange_rates_table.c.rate_to_twd)
        ).fetchall()
    return {row.currency: float(row.rate_to_twd) for row in rows}

# for converting non monthly salary to monthly salary
def period_multiplier(period: str | None) -> float | None:
    if period in ('monthly', 'per_month'):
        return 1.0
    if period in ('yearly', 'per_year'):
        return 1 / 12
    if period in ('hourly', 'hourly'):
        return HOURS_PER_MONTH
    logger.warning(f'Unrecognized salary period "{period}" - leaving uncoverted')
    return None

def normalize_cake_salary(
        amount: float | None,
        period: str | None,
        currency: str | None,
        rates: dict,
) -> float | None:
    # for cake, all the aforementioned information is known
    if amount is None:
        return None
    
    multiplier = period_multiplier(period)
    if multiplier is None:
        return None
    
    currency = (currency or 'TWD').upper()
    if currency == 'TWD':
        rate = 1.0
    else:
        rate = rates.get(currency)
        if rate is None:
            logger.warning(f"No cached exchange rate for currency '{currency}', skipping conversion")
            return None
    return round(amount * rate * multiplier, 2)

def normalize_104_salary(amount: float | None, salary_confidence: str) -> float | None:
    # the salary information on 104 is not complete so calculate the monthly salary
    # using customized metrics
    if amount is None or salary_confidence != 'monthly':
        return None
    return float(amount)

    