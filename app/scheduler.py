
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app import settings
from app.weather_service import sync_weather


# --------------------------------------------------
# 1. Configure logging
# --------------------------------------------------

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# --------------------------------------------------
# 2. Weather synchronization job
# --------------------------------------------------

async def scheduled_weather_sync():
    """
    Execute weather synchronization automatically.
    """

    logger.info("Scheduled weather synchronization started.")

    try:
        result = await sync_weather()

        logger.info(
            "Scheduled synchronization completed. "
            "Status: %s | Records processed: %s",
            result["status"],
            result["records_saved"],
        )

    except Exception:
        logger.exception(
            "Scheduled weather synchronization failed."
        )


# --------------------------------------------------
# 3. Start the scheduler
# --------------------------------------------------

async def run_scheduler():

    scheduler = AsyncIOScheduler(
        timezone=ZoneInfo("Asia/Kolkata")
    )

    scheduler.add_job(
        scheduled_weather_sync,
        trigger="interval",
        minutes=settings.UPDATE_INTERVAL_MINUTES,
        id="weather_sync_job",
        name="Automatic Weather Synchronization",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
        next_run_time=datetime.now(
            ZoneInfo("Asia/Kolkata")
        ),
    )

    scheduler.start()

    logger.info(
        "Weather scheduler started successfully."
    )

    logger.info(
        "Weather synchronization interval: %s minutes",
        settings.UPDATE_INTERVAL_MINUTES,
    )

    logger.info(
        "Next synchronization is scheduled immediately."
    )

    try:
        await asyncio.Event().wait()

    finally:
        scheduler.shutdown(wait=False)
        logger.info("Weather scheduler stopped.")


# --------------------------------------------------
# 4. Application entry point
# --------------------------------------------------

if __name__ == "__main__":

    try:
        asyncio.run(run_scheduler())

    except KeyboardInterrupt:
        logger.info("Scheduler interrupted by user.")
