## What is the project about 
The project consists of several web scrapers, which fetch the data related job postings from 
some of the major Taiwanese job searching websites including,
 
- [104](https://www.104.com.tw/)
- [1111](https://www.1111.com.tw/) (to be added)
- [Cake](https://www.cake.me/jobs)

## The workflow 
The pipeline looks like this
```
Sending tasks (Producer) → RabbitMQ → Worker (by which the scraper is conducted) → Data storage (MySQL)
```
## The tools used in this project
| tool | function | 
| --- | --- | 
| Python 3.11 | The main developing language |
| [uv](https://docs.astral.sh/uv/) | package management |
| [Celery](https://docs.celeryq.dev/) | asynchronous task queue|
| [RabbitMQ](https://www.rabbitmq.com/) | message  broker |
| [Flower](https://flower.readthedocs.io/) | Celery GUI |
| [Docker](https://www.docker.com/) | For running applications in a container|

## How to run this project 
You can choose to either run this project locally or using docker 😃

### Run the project locally  

#### Start the message broker: RabbitMQ
```text
docker compose -f rabbitmq.yml up -d
```
or
```text
docker compose -f rabbitmq-network.yml up -d 
```
⚠️ Note the difference between the files starting with *rabbitmq*
The first setup hosts the service locally while the second one run the service in a container.

#### Send the tasks to the broker 

    uv run python -m scraper.producer_{file_name}

#### Start the woker 
    uv run celery -A scraper.worker worker --loglevel=info
    uv run celery -A scraper.worker worker -Q 104_jobs,cake_jobs,exchange --loglevel=info 
    uv run celery -A scraper.worker worker -n {worker_name} -Q 104_jobs,cake_jobs,exchange --loglevel=info

*rename worker*
```text
uv run celery -A scraper.worker worker -n {name} --loglevel=info
```

### Alternatively, running it using Docker 🐋
#### Create a container

```text
docker run -it --rm ubuntu:22.04 bash
```

#### Create a network

```text
docker network create job_network
```

#### Run the procuder using docker compose to send tasks

```text
DOCKER_IMAGE_VERSION=0.0.7 docker compose -f docker-compose-producer.yml up -d
```

#### Run the worker using docker compose to execute tasks

```text
DOCKER_IMAGE_VERSION=0.0.7 docker compose -f docker-compose-worker.yml up -d
```