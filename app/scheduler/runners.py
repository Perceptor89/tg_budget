from apscheduler.triggers.interval import IntervalTrigger

from app.db_service import DatabaseAccessor
from app.rates_service import RateSeeker

from . import jobs
from .common import logger, scheduler


db = DatabaseAccessor()


@scheduler.scheduled_job(
    trigger=IntervalTrigger(minutes=5),
    id='get_reates_periodic_job',
)
async def get_rates_periodic_job() -> None:
    """Run getting rates daily job."""
    try:
        await jobs.get_rates(db, RateSeeker())
    except Exception as error:
        logger.exception('get_rates_periodic_job-E %s', error)
