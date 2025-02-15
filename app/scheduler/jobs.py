from typing import TYPE_CHECKING

from app.constants import USD_CODE, USDT_CODE
from app.db_service.models import ValuteRate

from .common import logger


if TYPE_CHECKING:
    from app.db_service import DatabaseAccessor
    from app.rates_service import RateSeeker


async def get_rates(db: 'DatabaseAccessor', seeker: 'RateSeeker') -> None:
    """Get valutes rates to USD for entries dates."""
    usd = await db.valute_repo.get_by_code(USD_CODE)

    for valute, date in await db.valute_rate_repo.get_unrated_dates(exclude=[USD_CODE, USDT_CODE]):
        try:
            rate = await seeker.get_rate(valute.code, date)
            if rate:
                await db.valute_rate_repo.create_item(
                    ValuteRate(
                        valute_from_id=usd.id,
                        valute_to_id=valute.id,
                        rate=rate,
                        date=date,
                    )
                )
        except Exception as error:
            logger.exception('get_rates-E code %s date %s error %s', valute.code, date.isoformat(), error)
