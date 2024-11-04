from functools import wraps
from logging import getLogger
from typing import Optional, Type, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from .models import _Base
from .session import session_factory


logger = getLogger('db')
T = TypeVar('T', bound=_Base)


def handle_session_errors(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        session = session_factory()
        try:
            result = await func(self, session, *args, **kwargs)
            await session.commit()
            return result
        except Exception as error:
            await session.rollback()
            logger.error(error)
        finally:
            await session.close()
    return wrapper


class _BaseRepo:
    _model: Type[T]

    @handle_session_errors
    async def create_item(self, session: AsyncSession, item: T) -> Optional[T]:
        session.add(item)
        logger.debug('%s -> %s', item.__class__.__name__, item.as_dict())
        return item

    @handle_session_errors
    async def update_item(self, session: AsyncSession, altered: T) -> Optional[T]:
        altered = await session.merge(altered)
        logger.debug('%s -> %s', altered.__class__.__name__, altered.as_dict())
        return altered


class TGMessageRepo(_BaseRepo):
    ...
