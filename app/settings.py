
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv


# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from the project .env file
load_dotenv(BASE_DIR / ".env")

# Load application configuration from YAML
CONFIG_FILE = BASE_DIR / "config.yaml"

with open(CONFIG_FILE, "r", encoding="utf-8") as file:
    CONFIG = yaml.safe_load(file)


# Application settings
APP_NAME = CONFIG["app"]["name"]
APP_ENVIRONMENT = CONFIG["app"]["environment"]
DEBUG = CONFIG["app"]["debug"]

# API settings
API_HOST = CONFIG["api"]["host"]
API_PORT = CONFIG["api"]["port"]

# Weather settings
WEATHER_CONFIG = CONFIG["weather"]
WEATHER_PROVIDER = WEATHER_CONFIG["provider"]
FORECAST_URL = WEATHER_CONFIG["forecast_url"]
FORECAST_HOURS = WEATHER_CONFIG["forecast_hours"]
UPDATE_INTERVAL_MINUTES = WEATHER_CONFIG["update_interval_minutes"]
CITIES = WEATHER_CONFIG["cities"]

# Database settings
DB_HOST = os.getenv("DB_HOST", "mysql")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("MYSQL_DATABASE")
DB_USER = os.getenv("MYSQL_USER")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD")

# Retention settings
RETENTION_DAYS = CONFIG["database"]["retention_days"]

# Logging settings
LOG_LEVEL = CONFIG["logging"]["level"]


# Validate required database credentials
if not all([DB_NAME, DB_USER, DB_PASSWORD]):
    raise ValueError(
        "Database configuration is incomplete. "
        "Check MYSQL_DATABASE, MYSQL_USER and MYSQL_PASSWORD in .env."
    )
