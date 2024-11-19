from functools import wraps
from logging import getLogger
from typing import List, Optional, Type, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Load, joinedload

from .models import Category, TGChat, TGMessage, TGUser, _Base
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

    @handle_session_errors
    async def _get_by_tg_id(
        self,
        session: AsyncSession,
        tg_id: int,
        options: Optional[List[Load]] = None,
    ) -> Optional[T]:
        query = select(self._model).where(self._model.tg_id == tg_id)
        if options:
            query = query.options(*options)
        result = await session.execute(query)
        return result.unique().scalar()


class TGChatRepository(_BaseRepo):

    _model = TGChat

    async def get_by_tg_id(self, tg_id: int) -> TGChat | None:
        options = [joinedload(TGChat.categories)]
        return await super()._get_by_tg_id(tg_id, options)


class TGMessageRepository(_BaseRepo):

    _model = TGMessage

    async def get_user_last_message(user_id: int) -> Optional[TGMessage]:
        pass


class TGUserRepository(_BaseRepo):

    _model = TGUser

    async def get_by_tg_id(self, tg_id: int) -> TGUser | None:
        return await super()._get_by_tg_id(tg_id)


class CategoryRepository(_BaseRepo):

    _model = Category


class DatabaseAccessor:
    chat_repo: TGChatRepository
    user_repo: TGUserRepository
    message_repo: TGMessageRepository

    def __init__(self) -> None:
        self.chat_repo = TGChatRepository()
        self.user_repo = TGUserRepository()
        self.message_repo = TGMessageRepository()
