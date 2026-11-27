
from contextlib import asynccontextmanager
from datetime import datetime
import logging
from typing import Any, Generic, Optional, TypeVar

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Query,
    Path,
    Request,
)
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app import settings
from app.database import get_db
from app.models import City, WeatherRecord, SyncHistory
from app.weather_service import sync_weather


# --------------------------------------------------
# 1. Logging and reusable API response schemas
# --------------------------------------------------

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    details: Optional[Any] = None


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None


# --------------------------------------------------
# 2. Data schemas
# --------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    application: str
    environment: str


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


class SyncHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    records_saved: int
    error_message: Optional[str] = None


# --------------------------------------------------
# 3. Common error response definitions
# --------------------------------------------------

ERROR_RESPONSES = {
    400: {
        "model": ApiResponse[None],
        "description": "Invalid request parameter.",
    },
    404: {
        "model": ApiResponse[None],
        "description": "Requested resource not found.",
    },
    422: {
        "model": ApiResponse[None],
        "description": "Request validation failed.",
    },
    500: {
        "model": ApiResponse[None],
        "description": "Internal server error.",
    },
}


# --------------------------------------------------
# 4. Application lifespan
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Weather Data Intelligence Platform started.")

    yield

    print("Weather Data Intelligence Platform stopped.")


# --------------------------------------------------
# 5. Swagger documentation metadata
# --------------------------------------------------

tags_metadata = [
    {
        "name": "Health",
        "description": "Check application health and availability.",
    },
    {
        "name": "Cities",
        "description": "Retrieve monitored cities.",
    },
    {
        "name": "Weather",
        "description": (
            "Retrieve current and hourly weather data "
            "and trigger weather synchronization."
        ),
    },
    {
        "name": "Monitoring",
        "description": "Monitor weather synchronization history.",
    },
]


# --------------------------------------------------
# 6. Create FastAPI application
# --------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "A Weather Data Intelligence Platform that collects "
        "and stores current weather observations and hourly "
        "forecasts for Indian cities.\n\n"
        "All endpoints use a standardized response structure "
        "containing success, message, data, and error."
    ),
    version="1.0.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)


# --------------------------------------------------
# 7. Centralized exception handlers
# --------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
):
    if isinstance(exc.detail, str):
        message = exc.detail
        details = None
    else:
        message = "The request could not be completed."
        details = exc.detail

    response = ApiResponse[None](
        success=False,
        message=message,
        data=None,
        error=ErrorDetail(
            code=f"HTTP_{exc.status_code}",
            details=details,
        ),
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(response),
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    response = ApiResponse[None](
        success=False,
        message="Request validation failed.",
        data=None,
        error=ErrorDetail(
            code="VALIDATION_ERROR",
            details=jsonable_encoder(exc.errors()),
        ),
    )

    return JSONResponse(
        status_code=422,
        content=jsonable_encoder(response),
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.exception("Unhandled API exception: %s", exc)

    response = ApiResponse[None](
        success=False,
        message="An unexpected server error occurred.",
        data=None,
        error=ErrorDetail(
            code="INTERNAL_SERVER_ERROR"
        ),
    )

    return JSONResponse(
        status_code=500,
        content=jsonable_encoder(response),
    )


# --------------------------------------------------
# 8. Root health endpoint
# --------------------------------------------------

@app.get(
    "/",
    response_model=ApiResponse[HealthResponse],
    tags=["Health"],
    summary="Check API health",
    description=(
        "Returns application health status, "
        "application name, and environment."
    ),
    responses={
        500: ERROR_RESPONSES[500],
    },
)
def health_check():

    health_data = HealthResponse(
        status="healthy",
        application=settings.APP_NAME,
        environment=settings.APP_ENVIRONMENT,
    )

    return ApiResponse[HealthResponse](
        success=True,
        message="API is healthy.",
        data=health_data,
    )


# --------------------------------------------------
# 9. List monitored cities
# --------------------------------------------------

@app.get(
    "/api/cities",
    response_model=ApiResponse[list[CityResponse]],
    tags=["Cities"],
    summary="List monitored cities",
    description=(
        "Returns all cities configured for weather monitoring, "
        "sorted alphabetically by city name."
    ),
    responses={
        500: ERROR_RESPONSES[500],
    },
)
def get_cities(db: Session = Depends(get_db)):

    cities = db.execute(
        select(City).order_by(City.name)
    ).scalars().all()

    return ApiResponse[list[CityResponse]](
        success=True,
        message="Cities retrieved successfully.",
        data=cities,
    )


# --------------------------------------------------
# 10. Retrieve weather records
# --------------------------------------------------

@app.get(
    "/api/weather",
    response_model=ApiResponse[list[WeatherResponse]],
    tags=["Weather"],
    summary="Retrieve weather records",
    description=(
        "Returns weather records across all monitored cities. "
        "Results are ordered by valid time, newest first."
    ),
    responses=ERROR_RESPONSES,
)
def get_weather(
    city: Optional[str] = Query(
        default=None,
        description="Optional city name filter.",
        examples=["Delhi"],
    ),
    record_type: Optional[str] = Query(
        default=None,
        description="Allowed values: current or hourly.",
        examples=["current", "hourly"],
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of records (1–1000).",
        examples=[100],
    ),
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

    records = [
        record for record, city_name in results
    ]

    return ApiResponse[list[WeatherResponse]](
        success=True,
        message="Weather records retrieved successfully.",
        data=records,
    )


# --------------------------------------------------
# 11. Retrieve weather for one city
# --------------------------------------------------

@app.get(
    "/api/weather/{city}",
    response_model=ApiResponse[list[WeatherResponse]],
    tags=["Weather"],
    summary="Retrieve weather for a city",
    description=(
        "Returns weather records for the specified monitored city. "
        "City matching is case-insensitive."
    ),
    responses=ERROR_RESPONSES,
)
def get_city_weather(
    city: str = Path(
        ...,
        description="Name of a monitored city.",
        examples=["Jaipur"],
    ),
    record_type: Optional[str] = Query(
        default=None,
        description="Allowed values: current or hourly.",
        examples=["hourly"],
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of records (1–1000).",
        examples=[100],
    ),
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

    return ApiResponse[list[WeatherResponse]](
        success=True,
        message=(
            f"Weather records for {city_record.name} "
            "retrieved successfully."
        ),
        data=records,
    )


# --------------------------------------------------
# 12. Manually trigger weather synchronization
# --------------------------------------------------

@app.post(
    "/api/weather/sync",
    response_model=ApiResponse[SyncResponse],
    tags=["Weather"],
    summary="Trigger weather synchronization",
    description=(
        "Manually starts the existing weather synchronization "
        "process and returns its status and records saved."
    ),
    responses={
        500: ERROR_RESPONSES[500],
    },
)
async def trigger_weather_sync():

    try:
        result = await sync_weather()

        return ApiResponse[SyncResponse](
            success=True,
            message="Weather synchronization completed successfully.",
            data=result,
        )

    except Exception:
        logger.exception("Weather synchronization failed.")

        raise HTTPException(
            status_code=500,
            detail="Weather synchronization failed.",
        )


# --------------------------------------------------
# 13. Retrieve synchronization history
# --------------------------------------------------

@app.get(
    "/api/sync-history",
    response_model=ApiResponse[list[SyncHistoryResponse]],
    tags=["Monitoring"],
    summary="Retrieve synchronization history",
    description=(
        "Returns recent synchronization jobs, "
        "ordered by start time with newest first."
    ),
    responses={
        422: ERROR_RESPONSES[422],
        500: ERROR_RESPONSES[500],
    },
)
def get_sync_history(
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of history records (1–100).",
        examples=[10],
    ),
    db: Session = Depends(get_db),
):

    history = db.execute(
        select(SyncHistory)
        .order_by(desc(SyncHistory.started_at))
        .limit(limit)
    ).scalars().all()

    history_data = [
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

    return ApiResponse[list[SyncHistoryResponse]](
        success=True,
        message="Synchronization history retrieved successfully.",
        data=history_data,
    )
