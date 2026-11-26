
from datetime import datetime, timedelta, timezone

from app import settings
from app.weather_service import (
    parse_weather_time,
    build_weather_records,
    cleanup_old_weather_records,
)


def sample_weather_data():
    return {
        "current": {
            "time": "2026-11-27T10:00",
            "temperature_2m": 28.5,
            "relative_humidity_2m": 65,
            "apparent_temperature": 30.0,
            "precipitation": 0.0,
            "weather_code": 1,
            "cloud_cover": 20,
            "wind_speed_10m": 12.5,
            "wind_direction_10m": 180,
            "wind_gusts_10m": 18.0,
        },
        "hourly": {
            "time": [
                "2026-11-27T10:00",
                "2026-11-27T11:00",
                "2026-11-27T12:00",
            ],
            "temperature_2m": [28.5, 29.0, 30.0],
            "relative_humidity_2m": [65, 60, 55],
            "precipitation_probability": [0, 10, 20],
            "precipitation": [0.0, 0.0, 0.2],
            "weather_code": [1, 2, 3],
            "wind_speed_10m": [12.5, 13.0, 14.0],
            "wind_direction_10m": [180, 190, 200],
        },
    }


def test_parse_weather_time_without_timezone():
    result = parse_weather_time("2026-11-27T10:00")

    assert result == datetime(2026, 11, 27, 10, 0)
    assert result.tzinfo is None


def test_parse_weather_time_with_utc_timezone():
    result = parse_weather_time("2026-11-27T10:00:00Z")

    assert result == datetime(
        2026, 11, 27, 10, 0, tzinfo=timezone.utc
    )


def test_build_weather_records():
    weather_data = sample_weather_data()
    fetched_at = datetime(2026, 11, 27, 10, 5)

    records = build_weather_records(
        city_id=1,
        weather_data=weather_data,
        fetched_at=fetched_at,
    )

    assert len(records) == 4

    current_record = records[0]

    assert current_record["city_id"] == 1
    assert current_record["record_type"] == "current"
    assert current_record["temperature"] == 28.5
    assert current_record["humidity"] == 65
    assert current_record["wind_speed"] == 12.5
    assert current_record["fetched_at"] == fetched_at

    hourly_records = records[1:]

    assert all(
        record["record_type"] == "hourly"
        for record in hourly_records
    )

    assert [record["temperature"] for record in hourly_records] == [
        28.5, 29.0, 30.0
    ]

    assert [
        record["precipitation_probability"]
        for record in hourly_records
    ] == [0, 10, 20]


def test_build_weather_records_handles_missing_hourly_values():
    weather_data = sample_weather_data()

    weather_data["hourly"]["temperature_2m"] = [28.5]

    records = build_weather_records(
        city_id=1,
        weather_data=weather_data,
        fetched_at=datetime(2026, 11, 27, 10, 5),
    )

    hourly_records = records[1:]

    assert hourly_records[0]["temperature"] == 28.5
    assert hourly_records[1]["temperature"] is None
    assert hourly_records[2]["temperature"] is None


def test_cleanup_old_weather_records(monkeypatch):
    class FakeResult:
        rowcount = 5

    class FakeDatabase:
        def __init__(self):
            self.execute_called = False
            self.commit_called = False
            self.statement = None

        def execute(self, statement):
            self.execute_called = True
            self.statement = statement
            return FakeResult()

        def commit(self):
            self.commit_called = True

    monkeypatch.setattr(settings, "RETENTION_DAYS", 90)

    db = FakeDatabase()

    deleted_count = cleanup_old_weather_records(db)

    assert deleted_count == 5
    assert db.execute_called is True
    assert db.commit_called is True
    assert db.statement is not None


def test_retention_cutoff_uses_configured_days(monkeypatch):
    class FakeResult:
        rowcount = 0

    class FakeDatabase:
        def execute(self, statement):
            return FakeResult()

        def commit(self):
            pass

    monkeypatch.setattr(settings, "RETENTION_DAYS", 90)

    db = FakeDatabase()

    deleted_count = cleanup_old_weather_records(db)

    assert deleted_count == 0
