from enum import Enum
from typing import Optional

from app.db_service.models import TGChat, TGUser
from app.db_service.repository import DatabaseAccessor
from app.redis_queue.base import QueueManager
from app.tg_service import TelegramClient
from app.tg_service.schemas import TGChatSchema, TGFromSchema, TGMessageSchema

# from app.db_service.repository import TGMessageRepo
from .handlers import CategoryAddHandler, CategoryListHandler


class AccountantCommandEnum(str, Enum):
    """Accountant command names."""

    CATEGORY_LIST = '/category_list'
    CATEGORY_ADD = '/category_add'
    CATEGORY_DELETE = '/category_delete'


class Accountant:
    db: DatabaseAccessor
    tg_client: Optional[TelegramClient] = None
    rq: QueueManager

    def __init__(self) -> None:
        self.db = DatabaseAccessor()
        self.handlers = {
            AccountantCommandEnum.CATEGORY_LIST.value: CategoryListHandler,
            AccountantCommandEnum.CATEGORY_ADD.value: CategoryAddHandler,
        }

    async def process_message(self, message: TGMessageSchema):
        chat = await self._get_or_create_chat(message.chat)
        user = await self._get_or_create_user(message.msg_from)
        if message.command:
            await self._execute_command(message.command, chat, user, message)

    async def _execute_command(
        self,
        command: AccountantCommandEnum,
        chat: TGChat,
        user: TGUser,
        message: TGMessageSchema,
    ):
        handler = self.handlers.get(command)
        if handler:
            handler = handler(self.db, self.tg_client)
            await handler.handle(chat, user, message)

    async def _get_or_create_chat(self, chat_schema: TGChatSchema) -> TGChat:
        if not (chat := await self.db.chat_repo.get_by_tg_id(chat_schema.tg_id)):
            data = chat_schema.model_dump(include={'tg_id', 'type', 'title'})
            chat = TGChat(**data)
            chat = await self.db.chat_repo.create_item(chat)

        return chat

    async def _get_or_create_user(self, user_schema: TGFromSchema) -> TGUser:
        if not (user := await self.db.user_repo.get_by_tg_id(user_schema.tg_id)):
            data = user_schema.model_dump(
                include={'tg_id', 'is_bot', 'first_name', 'username', 'language_code'},
            )
            user = TGUser(**data)
            user = await self.db.user_repo.create_item(user)

        return user
