
import httpx

from app import settings


# Weather parameters requested from Open-Meteo
CURRENT_WEATHER_FIELDS = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation",
    "weather_code",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
]

HOURLY_WEATHER_FIELDS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation_probability",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
    "wind_direction_10m",
]


async def fetch_weather(city: dict) -> dict:
    """
    Fetch current weather and hourly forecasts
    for a given city using the Open-Meteo API.
    """

    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "current": ",".join(CURRENT_WEATHER_FIELDS),
        "hourly": ",".join(HOURLY_WEATHER_FIELDS),
        "forecast_hours": settings.FORECAST_HOURS,
        "timezone": city["timezone"],
    }

    timeout = httpx.Timeout(20.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(
            settings.FORECAST_URL,
            params=params,
        )

        response.raise_for_status()

        weather_data = response.json()

    # Verify that the expected response sections exist.
    if "current" not in weather_data or "hourly" not in weather_data:
        raise ValueError(
            f"Invalid weather response received for {city['name']}."
        )

    return weather_data
