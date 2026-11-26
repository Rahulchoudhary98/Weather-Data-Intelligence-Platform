
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, delete
from sqlalchemy.dialects.mysql import insert

from app.database import SessionLocal
from app.models import City, WeatherRecord, SyncHistory
from app import settings
from app.external_api import fetch_weather


def register_cities(db):
    registered_count = 0

    for city_data in settings.CITIES:
        existing_city = db.execute(
            select(City).where(
                City.name == city_data["name"],
                City.country == city_data["country"],
            )
        ).scalar_one_or_none()

        if existing_city is None:
            new_city = City(
                name=city_data["name"],
                country=city_data["country"],
                latitude=city_data["latitude"],
                longitude=city_data["longitude"],
                timezone=city_data["timezone"],
            )
            db.add(new_city)
            registered_count += 1

    db.commit()
    return registered_count


def parse_weather_time(time_string):
    return datetime.fromisoformat(
        time_string.replace("Z", "+00:00")
    )


def build_weather_records(city_id, weather_data, fetched_at):
    records = []
    current = weather_data["current"]

    current_record = {
        "city_id": city_id,
        "record_type": "current",
        "temperature": current.get("temperature_2m"),
        "apparent_temperature": current.get("apparent_temperature"),
        "humidity": current.get("relative_humidity_2m"),
        "precipitation": current.get("precipitation"),
        "precipitation_probability": None,
        "weather_code": current.get("weather_code"),
        "cloud_cover": current.get("cloud_cover"),
        "wind_speed": current.get("wind_speed_10m"),
        "wind_direction": current.get("wind_direction_10m"),
        "wind_gusts": current.get("wind_gusts_10m"),
        "valid_time": parse_weather_time(current["time"]),
        "fetched_at": fetched_at,
    }

    records.append(current_record)

    hourly = weather_data["hourly"]
    times = hourly.get("time", [])

    for index, forecast_time in enumerate(times):

        def get_hourly_value(field):
            values = hourly.get(field, [])
            return values[index] if index < len(values) else None

        hourly_record = {
            "city_id": city_id,
            "record_type": "hourly",
            "temperature": get_hourly_value("temperature_2m"),
            "apparent_temperature": None,
            "humidity": get_hourly_value("relative_humidity_2m"),
            "precipitation": get_hourly_value("precipitation"),
            "precipitation_probability": get_hourly_value(
                "precipitation_probability"
            ),
            "weather_code": get_hourly_value("weather_code"),
            "cloud_cover": None,
            "wind_speed": get_hourly_value("wind_speed_10m"),
            "wind_direction": get_hourly_value("wind_direction_10m"),
            "wind_gusts": None,
            "valid_time": parse_weather_time(forecast_time),
            "fetched_at": fetched_at,
        }

        records.append(hourly_record)

    return records


def save_weather_records(db, records):
    if not records:
        return 0

    statement = insert(WeatherRecord).values(records)

    update_columns = [
        "temperature",
        "apparent_temperature",
        "humidity",
        "precipitation",
        "precipitation_probability",
        "weather_code",
        "cloud_cover",
        "wind_speed",
        "wind_direction",
        "wind_gusts",
        "fetched_at",
    ]

    update_values = {
        column: statement.inserted[column]
        for column in update_columns
    }

    statement = statement.on_duplicate_key_update(**update_values)

    db.execute(statement)

    return len(records)


def cleanup_old_weather_records(db):
    cutoff_time = (
        datetime.now(timezone.utc).replace(tzinfo=None)
        - timedelta(days=settings.RETENTION_DAYS)
    )

    result = db.execute(
        delete(WeatherRecord).where(
            WeatherRecord.fetched_at < cutoff_time
        )
    )

    db.commit()

    deleted_count = result.rowcount or 0

    print(
        f"Retention cleanup completed. "
        f"Deleted {deleted_count} expired records."
    )

    return deleted_count


async def sync_weather():
    db = SessionLocal()
    history_id = None

    try:
        register_cities(db)

        history = SyncHistory(
            status="running",
            records_saved=0,
        )

        db.add(history)
        db.commit()
        db.refresh(history)

        history_id = history.id

        fetched_at = datetime.now(timezone.utc).replace(tzinfo=None)

        cities = db.execute(
            select(City)
        ).scalars().all()

        total_records = 0

        for city in cities:
            city_config = {
                "name": city.name,
                "country": city.country,
                "latitude": city.latitude,
                "longitude": city.longitude,
                "timezone": city.timezone,
            }

            print(f"Fetching weather for {city.name}...")

            weather_data = await fetch_weather(city_config)

            records = build_weather_records(
                city.id,
                weather_data,
                fetched_at,
            )

            saved_count = save_weather_records(db, records)
            total_records += saved_count

            print(
                f"{city.name}: {saved_count} records processed"
            )

        db.commit()

        cleanup_old_weather_records(db)

        history = db.get(SyncHistory, history_id)

        history.status = "success"
        history.completed_at = (
            datetime.now(timezone.utc).replace(tzinfo=None)
        )
        history.records_saved = total_records

        db.commit()

        print("Weather synchronization completed successfully.")

        return {
            "status": "success",
            "records_saved": total_records,
        }

    except Exception as error:
        db.rollback()

        if history_id is not None:
            history = db.get(SyncHistory, history_id)

            if history is not None:
                history.status = "failed"
                history.completed_at = (
                    datetime.now(timezone.utc).replace(tzinfo=None)
                )
                history.error_message = str(error)[:5000]

                db.commit()

        print(f"Weather synchronization failed: {error}")

        raise

    finally:
        db.close()
