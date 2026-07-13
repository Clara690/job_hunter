# this is where all the environment variables are stored
import os
from dotenv import load_dotenv

load_dotenv()
# if the env variable is not set, use the default value
# in a dev environment, default value will be used while in production, env variable will be used

# RabbitMQ (queue) configuration
WORKER_ACCOUNT = os.environ.get("WORKER_ACCOUNT", "worker")
WORKER_PASSWORD = os.environ.get("WORKER_PASSWORD", "worker")

# RabbitMQ host address and port
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "127.0.0.1")
# convert to int as the default value is a string
# for connection to RabbitMQ, the value must be an integer
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", 5672))

# MySQL configuration
MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
MYSQL_ACCOUNT = os.environ.get("MYSQL_ACCOUNT", "root")
MYSQL_PASSWORD = os.environ['MYSQL_PASSWORD']
# MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "ppWgnb_mfGe2m_")
