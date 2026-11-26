
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from app.database import Base


class City(Base):
    __tablename__ = "cities"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    timezone = Column(String(100), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "name",
            "country",
            name="uq_city_name_country",
        ),
    )


class WeatherRecord(Base):
    __tablename__ = "weather_records"

    id = Column(Integer, primary_key=True, index=True)

    city_id = Column(
        Integer,
        ForeignKey("cities.id", ondelete="CASCADE"),
        nullable=False,
    )

    # current or hourly
    record_type = Column(String(20), nullable=False)

    temperature = Column(Float, nullable=True)
    apparent_temperature = Column(Float, nullable=True)
    humidity = Column(Integer, nullable=True)

    precipitation = Column(Float, nullable=True)
    precipitation_probability = Column(Integer, nullable=True)

    weather_code = Column(Integer, nullable=True)
    cloud_cover = Column(Integer, nullable=True)

    wind_speed = Column(Float, nullable=True)
    wind_direction = Column(Integer, nullable=True)
    wind_gusts = Column(Float, nullable=True)

    # Time the weather applies to
    valid_time = Column(DateTime, nullable=False)

    # Time the application collected the data
    fetched_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "city_id",
            "record_type",
            "valid_time",
            name="uq_weather_city_type_valid_time",
        ),
        Index("ix_weather_city_valid_time", "city_id", "valid_time"),
    )


class SyncHistory(Base):
    __tablename__ = "sync_history"

    id = Column(Integer, primary_key=True, index=True)

    started_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    completed_at = Column(DateTime, nullable=True)

    status = Column(
        String(20),
        nullable=False,
        default="running",
    )

    records_saved = Column(
        Integer,
        nullable=False,
        default=0,
    )

    error_message = Column(Text, nullable=True)
