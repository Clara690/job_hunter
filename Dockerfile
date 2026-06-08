# use the official Ubuntu 22.04 image as the base image
FROM ubuntu:22.04

# update package lists, and install curl and ca-certificates (required for downloading uv)
RUN apt-get update && \
    apt-get install -y curl ca-certificates

# install uv (for Python virtual environments and dependency management)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# install Python 3.11 using uv
RUN uv python install 3.11

# create /scraper directory
RUN mkdir /scraper

# copy all files from the current directory (same level as Dockerfile) to the /scraper directory in the container
COPY . /scraper/

# set  /scraper as the working directory, subsequent commands will be executed in this directory
WORKDIR /scraper/

# install all dependencies according to uv.lock (ensure environment consistency)
RUN uv sync --frozen

# set locale environment variables to avoid Python encoding issues
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# after starting the container, default to running bash (open terminal)
CMD ["/bin/bash"]
