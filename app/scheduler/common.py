from logging import getLogger

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import utc

from app.core.config import APSCHEDULER_DB_URL, ONE_MINUTE


logger = getLogger('apscheduler')

jobstores = {
    'default': SQLAlchemyJobStore(url=APSCHEDULER_DB_URL),
}
job_defaults = {
    'misfire_grace_time': ONE_MINUTE * 10,
}
scheduler = AsyncIOScheduler(
    timezone=utc,
    jobstores=jobstores,
    job_defaults=job_defaults,
)
