
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from app import settings
from app.database import get_db
from app.models import City, WeatherRecord, SyncHistory
from app.weather_service import sync_weather


# --------------------------------------------------
# 1. Pydantic response schemas
# --------------------------------------------------

class CityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    country: str
    latitude: float
    longitude: float
    timezone: str


class WeatherResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    city_id: int
    record_type: str

    temperature: Optional[float] = None
    apparent_temperature: Optional[float] = None
    humidity: Optional[int] = None

    precipitation: Optional[float] = None
    precipitation_probability: Optional[int] = None

    weather_code: Optional[int] = None
    cloud_cover: Optional[int] = None

    wind_speed: Optional[float] = None
    wind_direction: Optional[int] = None
    wind_gusts: Optional[float] = None

    valid_time: datetime
    fetched_at: datetime


class SyncResponse(BaseModel):
    status: str
    records_saved: int


# --------------------------------------------------
# 2. Application lifespan
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Weather Data Intelligence Platform started.")

    yield

    print("Weather Data Intelligence Platform stopped.")


# --------------------------------------------------
# 3. Create FastAPI application
# --------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "A Weather Data Intelligence Platform "
        "that collects and stores current weather "
        "and hourly forecasts for Indian cities."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# --------------------------------------------------
# 4. Root health endpoint
# --------------------------------------------------

@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "application": settings.APP_NAME,
        "environment": settings.APP_ENVIRONMENT,
    }


# --------------------------------------------------
# 5. List monitored cities
# --------------------------------------------------

@app.get(
    "/api/cities",
    response_model=list[CityResponse],
    tags=["Cities"],
)
def get_cities(db: Session = Depends(get_db)):

    cities = db.execute(
        select(City).order_by(City.name)
    ).scalars().all()

    return cities


# --------------------------------------------------
# 6. Retrieve weather records
# --------------------------------------------------

@app.get(
    "/api/weather",
    response_model=list[WeatherResponse],
    tags=["Weather"],
)
def get_weather(
    city: Optional[str] = Query(default=None),
    record_type: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):

    query = (
        select(WeatherRecord, City.name)
        .join(City, WeatherRecord.city_id == City.id)
    )

    if city:

        query = query.where(
            City.name.ilike(city)
        )

    if record_type:

        if record_type not in ["current", "hourly"]:
            raise HTTPException(
                status_code=400,
                detail="record_type must be current or hourly.",
            )

        query = query.where(
            WeatherRecord.record_type == record_type
        )

    query = query.order_by(
        desc(WeatherRecord.valid_time)
    ).limit(limit)

    results = db.execute(query).all()

    return [record for record, city_name in results]


# --------------------------------------------------
# 7. Retrieve weather for one city
# --------------------------------------------------

@app.get(
    "/api/weather/{city}",
    response_model=list[WeatherResponse],
    tags=["Weather"],
)
def get_city_weather(
    city: str,
    record_type: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):

    city_record = db.execute(
        select(City).where(
            City.name.ilike(city)
        )
    ).scalar_one_or_none()

    if city_record is None:

        raise HTTPException(
            status_code=404,
            detail=f"City '{city}' was not found.",
        )

    query = select(WeatherRecord).where(
        WeatherRecord.city_id == city_record.id
    )

    if record_type:

        if record_type not in ["current", "hourly"]:
            raise HTTPException(
                status_code=400,
                detail="record_type must be current or hourly.",
            )

        query = query.where(
            WeatherRecord.record_type == record_type
        )

    query = query.order_by(
        desc(WeatherRecord.valid_time)
    ).limit(limit)

    records = db.execute(query).scalars().all()

    return records


# --------------------------------------------------
# 8. Manually trigger weather synchronization
# --------------------------------------------------

@app.post(
    "/api/weather/sync",
    response_model=SyncResponse,
    tags=["Weather"],
)
async def trigger_weather_sync():

    try:

        result = await sync_weather()

        return result

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Weather synchronization failed: {str(error)}",
        )


# --------------------------------------------------
# 9. Retrieve synchronization history
# --------------------------------------------------

@app.get(
    "/api/sync-history",
    tags=["Monitoring"],
)
def get_sync_history(
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):

    history = db.execute(
        select(SyncHistory)
        .order_by(desc(SyncHistory.started_at))
        .limit(limit)
    ).scalars().all()

    return [
        {
            "id": item.id,
            "started_at": item.started_at,
            "completed_at": item.completed_at,
            "status": item.status,
            "records_saved": item.records_saved,
            "error_message": item.error_message,
        }
        for item in history
    ]
