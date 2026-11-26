
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY ./app ./app
COPY ./migrations ./migrations
COPY ./alembic.ini ./alembic.ini
COPY ./config.yaml ./config.yaml

EXPOSE 8000
