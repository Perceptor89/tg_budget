
from typing import Protocol, Union

from app.accountant.messages import NO_CATEGORIES
from app.db_service.models import TGChat, TGUser
from app.db_service.repository import DatabaseAccessor
from app.tg_service import api as tg_api
from app.tg_service.client import SendTaskSchema, TelegramClient
from app.tg_service.schemas import (
    ForceReplySchema,
    ReplyParametersRequestSchema,
    SendMessageRequestSchema,
    TGMessageSchema,
)


CATEGORY_LIMIT = 12


class CommandHandler(Protocol):

    db: DatabaseAccessor
    tg: TelegramClient

    def __init__(self, db: DatabaseAccessor, tg: TelegramClient) -> None:
        super().__init__()
        self.db = db
        self.tg = tg

    async def handle(self, chat: TGChat, user: TGUser, message: TGMessageSchema) -> None:
        ...

    async def answer(
        self,
        message: TGMessageSchema,
        text: str,
        reply_markup: Union[ForceReplySchema, None] = None,
    ) -> SendTaskSchema:
        reply_parameters = ReplyParametersRequestSchema(
            message_id=message.message_id,
            chat_id=message.chat.tg_id,
        )
        request = SendMessageRequestSchema(
            chat_id=message.chat.tg_id,
            text=text,
            reply_parameters=reply_parameters,
        )
        if reply_markup:
            request.reply_markup = reply_markup
        return await self.tg.send(tg_api.SendMessage, request)


class CategoryListHandler(CommandHandler):
    async def handle(self, chat: TGChat, _: TGUser, message: TGMessageSchema) -> None:
        text = '\n'.join('.' + c.name for c in chat.categories)
        text = text or NO_CATEGORIES
        await self.answer(message, text)


class CategoryAddHandler(CommandHandler):
    async def handle(self, chat: TGChat, user: TGUser, message: TGMessageSchema) -> None:
        if len(chat.categories) >= CATEGORY_LIMIT:
            text = CATEGORY_LIMIT.format(CATEGORY_LIMIT)
            reply_markup = None
        else:
            text = 'Введите название категории'
            reply_markup = ForceReplySchema(input_field_placeholder='название категории') 
        await self.answer(message, text, reply_markup)
