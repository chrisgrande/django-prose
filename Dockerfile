FROM python:3.14-slim-bookworm

ENV POETRY_VERSION=1.8.3 \
    POETRY_HOME=/opt/poetry \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    PATH="/opt/poetry/bin:$PATH"

RUN pip install "poetry==${POETRY_VERSION}"

WORKDIR /usr/src/app

COPY pyproject.toml poetry.lock ./
RUN poetry install

COPY ./ ./
