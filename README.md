## What is the project about 
The project consists of several web scrapers, which fetch the data related job postings from 
some of the major Taiwanese job searching websites including [104](https://www.104.com.tw/), [1111](https://www.1111.com.tw/) and [Cake](https://www.cake.me/jobs).

## The workflow 
The pipeline looks like this
```
Sending tasks (Producer) → RabbitMQ → Worker (by which the scraper is conducted) → Data storage (MySQL)
```
## The tools used 
| tool | function | 
| --- | --- | --- |
| Python 3.11 | The main developing language |
| [uv](https://docs.astral.sh/uv/) | package management |
| [Celery](https://docs.celeryq.dev/) | asynchronous task queue|
| [RabbitMQ](https://www.rabbitmq.com/) | broker |
| [Flower](https://flower.readthedocs.io/) | Celery GUI |

## How to run this project 
### set up 

#### start the message broker: RabbitMQ

    docker compose -f rabbitmq.yml up -d
    docker compose -f rabbitmq-network.yml up -d 
    
    ⚠️ Note the difference between the files starting with *rabbitmq*

#### send the tasks to the broker 

    uv run python -m scraper.producer_{file_name}

#### start the woker 
    uv run celery -A scraper.worker worker --loglevel=info