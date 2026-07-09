from celery import Celery
from loguru import logger 

# read the connection settings for RabbitMQ from config.py
from scraper.config import (
    RABBITMQ_HOST, 
    RABBITMQ_PORT,
    WORKER_ACCOUNT, 
    WORKER_PASSWORD)

# print the loaded environment variables for debugging
logger.info(f"""
    RABBITMQ_HOST: {RABBITMQ_HOST}
    RABBITMQ_PORT: {RABBITMQ_PORT}
    WORKER_ACCOUNT: {WORKER_ACCOUNT}
    WORKER_PASSWORD: {WORKER_PASSWORD}
""")

# create a Celery instance and configure the broker URL for RabbitMQ
# "task" is the name of the Celery instance
app = Celery("task", 
             # the tasks to incude in this worker
             # only tasks that are defined using @app.task() decorator in the specified module will be registered with this Celery instance
             include=[
                 "scraper.tasks_104_scraper", # scraping 104
                 "scraper.tasks_cake_scraper", # scraping Cake
                 "scraper.tasks_get_exchange_rate" # fetch exchange rate data
             ],
            #  broker=f"pyamqp://{WORKER_ACCOUNT}:{WORKER_PASSWORD}@rabbitmq:{RABBITMQ_PORT}/")
             broker=f"amqp://{WORKER_ACCOUNT}:{WORKER_PASSWORD}@{RABBITMQ_HOST}:{RABBITMQ_PORT}//")

