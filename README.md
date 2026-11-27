# Weather Data Intelligence Platform

A learning-focused weather data platform built using **Python, FastAPI, MySQL, SQLAlchemy, Docker Compose, and Open-Meteo**.

The platform collects current weather conditions and hourly forecasts for Jaipur, Delhi, and Mumbai, stores the data in MySQL, and exposes it through REST APIs.

## Features

- Current weather data collection.
- Hourly weather forecasts for the next 24 hours.
- Automatic synchronization every 60 minutes.
- Manual synchronization through a REST API.
- Persistent MySQL storage.
- Independent API and scheduler services.
- Configurable monitored cities and collection settings.
- Duplicate-safe weather record updates.
- Synchronization history and error tracking.
- Automatic deletion of weather records older than 90 days.
- Standardized API response structure.
- Interactive Swagger API documentation.
- Automated unit tests.

## Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.14 |
| API Framework | FastAPI |
| API Server | Uvicorn |
| Database | MySQL 8.4 |
| ORM | SQLAlchemy |
| Database Migrations | Alembic |
| HTTP Client | HTTPX |
| Configuration | YAML and environment variables |
| Scheduler | APScheduler |
| Validation | Pydantic |
| Testing | Pytest |
| Containerization | Docker and Docker Compose |
| Weather Provider | Open-Meteo |

## Architecture

The platform consists of three independent services:

1. **MySQL:** Stores city information, weather records, and synchronization history.
2. **FastAPI:** Exposes REST endpoints for health checks, cities, weather records, manual synchronization, and synchronization history.
3. **Scheduler:** Automatically collects weather data at the configured interval.

### Data Flow

1. The scheduler requests weather data from Open-Meteo.
2. The received data is validated and transformed.
3. SQLAlchemy saves or updates weather records in MySQL.
4. Synchronization status and processing information are recorded.
5. Expired weather records are removed according to the retention setting.
6. API clients retrieve stored information through FastAPI.

## Monitored Cities

| City | Country | Timezone |
|---|---|---|
| Jaipur | India | Asia/Kolkata |
| Delhi | India | Asia/Kolkata |
| Mumbai | India | Asia/Kolkata |

## Database Design

### 1. cities

Stores city names, countries, geographic coordinates, and timezones.

### 2. weather_records

Stores current weather and hourly forecast records, including:

- Temperature
- Apparent temperature
- Humidity
- Precipitation
- Precipitation probability
- Weather code
- Cloud cover
- Wind speed
- Wind direction
- Wind gusts
- Valid time
- Fetch time

A unique constraint on city, record type, and valid time prevents duplicate records for the same forecast timestamp. New synchronization results update existing records where appropriate.

### 3. sync_history

Tracks synchronization start time, completion time, status, processed record count, and errors.

## Project Structure

```text
api-mysql-docker/
│
├── app/
│   ├── __init__.py
│   ├── database.py
│   ├── external_api.py
│   ├── main.py
│   ├── models.py
│   ├── scheduler.py
│   ├── settings.py
│   └── weather_service.py
│
├── migrations/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
│
├── tests/
│   └── test_weather_service.py
│
├── .env.example
├── .gitignore
├── .dockerignore
├── alembic.ini
├── compose.yaml
├── config.yaml
├── Dockerfile
├── README.md
└── requirements.txt
```

> The actual `.env` file and virtual environment are kept locally and are not committed to GitHub.

## Configuration

Application settings are maintained in `config.yaml`.

The configuration includes:

- Application name and environment.
- API host and port.
- Weather provider URLs.
- Forecast horizon.
- Synchronization interval.
- Monitored cities.
- Database retention period.
- Logging level.

Database credentials are stored separately in `.env`.

Never commit `.env` or expose database passwords.

## Environment Setup

### Prerequisites

- Python 3.14
- Docker Desktop
- Docker Compose
- Git

### 1. Clone the repository

```powershell
git clone https://github.com/Rahulchoudhary98/Weather-Data-Intelligence-Platform.git

cd Weather-Data-Intelligence-Platform
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv

.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure environment variables

Create `.env` using `.env.example` as a template.

Set your own database credentials. Do not commit `.env`.

### 5. Start Docker services

```powershell
docker compose up -d --build
```

### 6. Check service status

```powershell
docker compose ps
```

### 7. Apply database migrations

```powershell
docker compose exec api alembic upgrade head
```

The initial migration creates the required database tables.

### 8. Access the API documentation

Once the API is running, visit:

**Swagger UI:** http://localhost:8000/docs

**OpenAPI JSON:** http://localhost:8000/openapi.json

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Application health |
| GET | `/api/cities` | List monitored cities |
| GET | `/api/weather` | Retrieve weather records |
| GET | `/api/weather/{city}` | Retrieve weather for a city |
| POST | `/api/weather/sync` | Trigger manual synchronization |
| GET | `/api/sync-history` | Retrieve synchronization history |

### Example Requests

**Get application health**

```http
GET /
```

**Get monitored cities**

```http
GET /api/cities
```

**Get current weather**

```http
GET /api/weather?record_type=current
```

**Get hourly forecasts for Jaipur**

```http
GET /api/weather/Jaipur?record_type=hourly&limit=24
```

**Trigger manual synchronization**

```http
POST /api/weather/sync
```

**Retrieve synchronization history**

```http
GET /api/sync-history
```

## Standardized API Responses

All API endpoints follow a consistent response structure.

### Successful Response

```json
{
  "success": true,
  "message": "API is healthy.",
  "data": {
    "status": "healthy",
    "application": "Weather Data Intelligence Platform",
    "environment": "development"
  },
  "error": null
}
```

### Error Response

```json
{
  "success": false,
  "message": "Request validation failed.",
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "details": []
  }
}
```

The standardized response format makes API results easier to consume and handle consistently.

## Automatic Synchronization

The scheduler runs as an independent Docker service.

The default configuration collects weather data every 60 minutes. An initial synchronization is also triggered when the scheduler starts.

**View scheduler logs:**

```powershell
docker compose logs --tail=50 scheduler
```

**View API logs:**

```powershell
docker compose logs --tail=50 api
```

## Data Retention

The default retention period is 90 days.

Records are evaluated using `fetched_at`. Records older than the configured retention period are deleted after a successful weather synchronization.

The retention period can be changed in `config.yaml`.

## Running Tests

Activate the virtual environment and execute:

```powershell
python -m pytest -v
```

The tests validate weather timestamp parsing, record transformation, missing values, and retention cleanup using test data and a fake database.

## Useful Docker Commands

**Check running services**

```powershell
docker compose ps
```

**View all service logs**

```powershell
docker compose logs --tail=100
```

**Restart services**

```powershell
docker compose restart
```

**Stop services without deleting persistent data**

```powershell
docker compose stop
```

**Start existing services again**

```powershell
docker compose start
```

> Do not use `docker compose down -v` unless you intentionally want to delete the project's persistent database volume.

## Data Provider and Attribution

Weather data is provided by [Open-Meteo](https://open-meteo.com/).

Please review the provider's terms and attribution requirements before public or commercial deployment.

## Project Scope and Limitations

This is a learning-focused data engineering project demonstrating:

- REST API development.
- External data collection and processing.
- Relational database design and persistence.
- Scheduled background processing.
- Docker-based application deployment.
- Configuration and environment management.
- Database migrations.
- API documentation and response standardization.
- Automated testing.

It is not intended to be a production-ready weather forecasting service.

### Potential Future Improvements

- Pagination and advanced API filtering.
- API authentication.
- Structured logging and monitoring.
- Database backup and recovery procedures.
- Integration and end-to-end tests.
- Deployment to a cloud environment.