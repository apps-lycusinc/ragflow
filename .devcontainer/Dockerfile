FROM mcr.microsoft.com/devcontainers/base:noble

ENV PYTHONUNBUFFERED 1

RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends libjemalloc-dev
