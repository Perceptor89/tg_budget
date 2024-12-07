from functools import wraps
from logging import getLogger
from typing import List, Optional, Type, TypeVar

from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Load, contains_eager, joinedload

from app.db_service.enums import BudgetItemTypeEnum

from .models import (
    BudgetItem,
    ChatValute,
    Category,
    ChatBudgetItem,
    Entry,
    TGChat,
    TGUser,
    TGUserState,
    _Base,
    Valute,
)
from .session import session_factory


logger = getLogger('db')
T = TypeVar('T', bound=_Base)


def handle_session(function):
    @wraps(function)
    async def wrapper(self, *args, **kwargs):
        session = session_factory()
        try:
            result = await function(self, session, *args, **kwargs)
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

    @handle_session
    async def create_item(self, session: AsyncSession, item: T) -> Optional[T]:
        session.add(item)
        await session.flush([item])
        logger.debug('%s -> %s', item.__class__.__name__, item.as_dict())
        return item

    @handle_session
    async def update_item(self, session: AsyncSession, altered: T) -> Optional[T]:
        altered = await session.merge(altered)
        logger.debug('%s -> %s', altered.__class__.__name__, altered.as_dict())
        return altered

    @handle_session
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

    @handle_session
    async def _get_by_id(
        self,
        session: AsyncSession,
        item_id: int,
    ) -> Optional[T]:
        query = select(self._model).where(self._model.id == item_id)
        result = await session.execute(query)
        return result.scalar()

    @handle_session
    async def _get_by_name(
        self,
        session: AsyncSession,
        name: str,
    ) -> Optional[T]:
        query = select(self._model).where(self._model.name == name)
        result = await session.execute(query)
        return result.scalar()


class TGChatRepository(_BaseRepo):

    _model = TGChat

    @handle_session
    async def get_by_tg_id(self, session: AsyncSession, tg_id: int) -> TGChat | None:
        query = select(TGChat)\
            .outerjoin(ChatBudgetItem, ChatBudgetItem.chat_id == TGChat.id)\
            .outerjoin(Category, Category.id == ChatBudgetItem.category_id)\
            .outerjoin(BudgetItem, BudgetItem.id == ChatBudgetItem.budget_item_id)\
            .options(
                contains_eager(TGChat.categories).contains_eager(Category.budget_items),
                joinedload(TGChat.valutes),
            ).where(TGChat.tg_id == tg_id)
        result = await session.execute(query)
        return result.unique().scalar()


class TGUserRepository(_BaseRepo):

    _model = TGUser

    async def get_by_tg_id(self, tg_id: int) -> TGUser | None:
        return await super()._get_by_tg_id(tg_id)


class UserStateRepository(_BaseRepo):

    _model = TGUserState

    @handle_session
    async def get_tg_user_state(
        self, session: AsyncSession, tg_user_id: int,
    ) -> Optional[TGUserState]:
        query = select(TGUserState).where(TGUserState.tg_user_id == tg_user_id)
        result = await session.execute(query)
        return result.scalar()


class ChatCategoryBudgetItemRepository(_BaseRepo):

    _model = ChatBudgetItem

    @handle_session
    async def get_chat_budget_item(
        self,
        session: AsyncSession,
        chat_id: int,
        category_id: int,
        budget_item_name: Optional[str] = None,
        budget_item_type: Optional[BudgetItemTypeEnum] = None,
        budget_item_id: Optional[int] = None,
    ) -> Optional[ChatBudgetItem]:
        if not budget_item_id and not (budget_item_name and budget_item_type):
            raise ValueError('No budget_item specified')
        query = select(
            ChatBudgetItem,
        ).outerjoin(
            BudgetItem, BudgetItem.id == ChatBudgetItem.budget_item_id,
        ).where(
            and_(
                ChatBudgetItem.chat_id == chat_id,
                ChatBudgetItem.category_id == category_id,
            ),
        )
        if budget_item_id:
            query = query.where(ChatBudgetItem.budget_item_id == budget_item_id)
        else:
            query = query.where(
                and_(
                    BudgetItem.name == budget_item_name,
                    BudgetItem.type == budget_item_type.value,
                ),
            )
        result = await session.execute(query)
        return result.scalar()

    @handle_session
    async def get_no_budget_item_row(
        self, session: AsyncSession, chat_id: int, category_id: int,
    ) -> Optional[ChatBudgetItem]:
        query = select(ChatBudgetItem).where(
            and_(
                ChatBudgetItem.chat_id == chat_id,
                ChatBudgetItem.category_id == category_id,
                ChatBudgetItem.budget_item_id.is_(None),
            ),
        )
        result = await session.execute(query)
        return result.scalar()


class BudgetItemRepository(_BaseRepo):

    _model = BudgetItem

    async def get_by_name(self, name: str) -> Optional[BudgetItem]:
        return await super()._get_by_name(name)


class CategoryRepository(_BaseRepo):

    _model = Category

    async def get_by_id(self, category_id: int) -> Optional[Category]:
        return await super()._get_by_id(category_id)


class ValuteRepository(_BaseRepo):

    _model = Valute

    async def get_by_name(self, name: str) -> Optional[Valute]:
        return await super()._get_by_name(name)

    @handle_session
    async def get_by_code(self, session: AsyncSession, code: str) -> Optional[Valute]:
        query = select(self._model).where(self._model.code == code)
        result = await session.execute(query)
        return result.scalar()


class ChatValuteRepository(_BaseRepo):

    _model = ChatValute


class EntryRepository(_BaseRepo):

    _model = Entry


class DatabaseAccessor:
    chat_repo: TGChatRepository
    user_repo: TGUserRepository
    state_repo: UserStateRepository
    budget_item_repo: BudgetItemRepository
    category_repo = CategoryRepository
    chat_budget_item_repo: ChatCategoryBudgetItemRepository
    valute_repo: ValuteRepository
    entry_repo: EntryRepository
    chat_valute_repo: ChatValuteRepository

    def __init__(self) -> None:
        self.chat_repo = TGChatRepository()
        self.user_repo = TGUserRepository()
        self.state_repo = UserStateRepository()
        self.budget_item_repo = BudgetItemRepository()
        self.category_repo = CategoryRepository()
        self.chat_budget_item_repo = ChatCategoryBudgetItemRepository()
        self.valute_repo = ValuteRepository()
        self.entry_repo = EntryRepository()
        self.chat_valute_repo = ChatValuteRepository()
