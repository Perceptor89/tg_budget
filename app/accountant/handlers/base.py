
import enum
from abc import abstractmethod
from typing import Optional, Union

from app import exceptoions
from app.accountant import constants
from app.db_service.models import Category, ChatValute, TGChat, TGUser, TGUserState, Valute
from app.db_service.repository import DatabaseAccessor
from app.tg_service import api as tg_api
from app.tg_service import schemas
from app.tg_service.client import SendTaskSchema, TelegramClient
from app.tg_service.editor import TGMessageEditor
from app.tg_service.schemas import (
    DeleteMessageRequestSchema,
    EditMessageReplyMarkupRequestSchema,
    EditMessageTextRequestSchema,
    ForceReplySchema,
    InlineKeyboardMarkup,
    ReplyParametersRequestSchema,
    SendMessageRequestSchema,
    SendPhotoRequestSchema,
    TGCallbackQuerySchema,
    TGMessageSchema,
)


class BaseHandler:
    """Base handler."""

    db: DatabaseAccessor
    tg: TelegramClient
    editor: TGMessageEditor
    chat: TGChat
    user: TGUser
    update: Union[TGMessageSchema, TGCallbackQuerySchema]
    state: TGUserState

    def __init__(self, db: DatabaseAccessor, tg: TelegramClient, editor: TGMessageEditor,
                 chat: TGChat, user: TGUser, update: Union[TGMessageSchema, TGCallbackQuerySchema],
                 state: TGUserState) -> None:
        self.db = db
        self.tg = tg
        self.editor = editor
        self.chat = chat
        self.user = user
        self.update = update
        self.state = state

    @abstractmethod
    async def handle(self) -> None:
        """Handle Telegram update."""

    async def delete_message(self, message_id: int) -> SendTaskSchema:
        """Delete message."""
        request = DeleteMessageRequestSchema(chat_id=self.chat.tg_id,
                                             message_id=message_id)
        return await self.tg.send(tg_api.DeleteMessage, request)

    async def delete_income_messages(
            self, delete_reply_to_msg: bool = False) -> list[SendTaskSchema]:
        """Delete request messages."""
        if isinstance(self.update, TGCallbackQuerySchema):
            messages = [self.update.message]
        else:
            messages = [self.update]
            reply_to_msg = self.update.reply_to_message
            if delete_reply_to_msg and reply_to_msg:
                messages.append(reply_to_msg)
        tasks = []
        for msg in messages:
            tasks.append(await self.delete_message(msg.message_id))
        return tasks

    async def set_state(self, state_name: enum.Enum, state_data: dict) -> None:
        """Set user state data."""
        self.state.name = state_name.value
        self.state.data_raw = state_data
        self.state = await self.db.state_repo.update_item(self.state)

    async def wait_task_result(
            self, task: SendTaskSchema, next_state: enum.Enum, state_data: Optional[dict] = None,
            response_to_state: set[str] = None) -> Optional[schemas.ResponseSchema]:
        """Wait for task result and update state."""
        state_data = state_data or {}
        response_to_state = response_to_state or set()
        await task.event.wait()
        response: Union[None, schemas.SendMessageResponseSchema] = task.response
        if response:
            for key in response_to_state:
                if key == 'message_id':
                    state_data[key] = response.result.message_id
            await self.set_state(next_state, state_data)
        return response

    async def send_message(
        self,
        text: str,
        reply_markup: Union[ForceReplySchema, InlineKeyboardMarkup, None] = None,
        is_reply: bool = False,
        parse_mode: str = 'MarkdownV2'
    ) -> SendTaskSchema:
        """Send message to chat."""
        reply_parameters = None
        text = self.editor.escape(text)
        if is_reply:
            reply_parameters = ReplyParametersRequestSchema(message_id=self.update.message_id,
                                                            chat_id=self.chat.tg_id)
        request = SendMessageRequestSchema(chat_id=self.chat.tg_id,
                                           text=text,
                                           reply_parameters=reply_parameters,
                                           reply_markup=reply_markup,
                                           parse_mode=parse_mode)
        return await self.tg.send(tg_api.SendMessage, request)

    async def edit_message(
        self,
        message_id: int,
        text: str,
        reply_markup: Union[ForceReplySchema, InlineKeyboardMarkup, None] = None,
        parse_mode: str = 'MarkdownV2'
    ) -> SendTaskSchema:
        """Edit Telegram message text and keyboard."""
        text = self.editor.escape(text)
        request = EditMessageTextRequestSchema(chat_id=self.chat.tg_id,
                                               message_id=message_id,
                                               text=text,
                                               reply_markup=reply_markup,
                                               parse_mode=parse_mode)
        return await self.tg.send(tg_api.EditMessageText, request)

    async def send_photo(
        self,
        photo: bytes,
        caption: Optional[str] = None,
        reply_markup: Union[ForceReplySchema, InlineKeyboardMarkup, None] = None
    ) -> SendTaskSchema:
        """Send photo to chat."""
        request = {
            'chat_id': self.chat.tg_id,
            'caption': caption,
            'reply_markup': reply_markup.model_dump_json() if reply_markup else None,
            'files': {'photo': photo}
        }
        request = SendPhotoRequestSchema.model_validate(request)
        return await self.tg.send(tg_api.SendPhoto, request)

    def get_selected_category(self) -> Category:
        """Get selected category."""
        category_name = self.update.data
        if not (category := [c for c in self.chat.categories if c.name == category_name]):
            raise exceptoions.AccountantError(f'category[{category_name}] not found')
        return category[0]

    def get_state_category(self) -> Category:
        """Get state category."""
        error: Optional[str] = None
        if not (category_id := self.state.data.category_id):
            error = 'no state category id'
        elif not (category := [c for c in self.chat.categories if c.id == category_id]):
            error = f'no category[{category_id}] in chat[{self.chat.title}]'
        if error:
            raise exceptoions.AccountantError(error)
        return category[0]

    async def get_chat_valutes(self) -> list[Valute]:
        """Get chat valutes."""
        chat = self.chat
        valutes = chat.valutes

        if not valutes:
            rub_valute = await self.db.valute_repo.get_by_code(code=constants.DEFAULT_VALUTE_CODE)
            if not rub_valute:
                rub_valute = await self.db.valute_repo.create_item(
                    Valute(name=constants.DEFAULT_VALUTE_NAME,
                           symbol=constants.DEFAULT_VALUTE_SYMBOL,
                           code=constants.DEFAULT_VALUTE_CODE))
            chat_valute = ChatValute(chat_id=chat.id, valute_id=rub_valute.id)
            chat.valutes = [rub_valute]
            await self.db.chat_valute_repo.create_item(chat_valute)
        return chat.valutes

    def get_selected_valute(self, chat: TGChat, callback: TGCallbackQuerySchema) -> Valute:
        """Get selected valute."""
        valute_code = callback.data
        if not (valute := [v for v in chat.valutes if v.code == valute_code]):
            raise exceptoions.AccountantError(f'no valute[{valute_code}] in chat[{chat.title}]')
        return valute[0]

    def get_state_valute(self) -> Valute:
        """Get state valute."""
        error: Optional[str] = None
        if not (valute_id := self.state.data.valute_id):
            error = 'state valute_id not found'
        elif not (valute := [v for v in self.chat.valutes if v.id == valute_id]):
            error = 'state valute not found'
        if error:
            raise exceptoions.AccountantError(error)
        return valute[0]

    async def edit_message_reply_markup(
        self,
        message_id: TGMessageSchema,
        reply_markup: Union[ForceReplySchema, InlineKeyboardMarkup, None] = None
    ) -> SendTaskSchema:
        """Edit message reply markup."""
        request = EditMessageReplyMarkupRequestSchema(chat_id=self.chat.tg_id,
                                                      message_id=message_id,
                                                      reply_markup=reply_markup)
        return await self.tg.send(tg_api.EditMessageReplyMarkup, request)

    @property
    def user_mention(self) -> str:
        """Get user mention."""
        username = self.user.username
        if username:
            return self.editor.get_mention(username)
        else:
            return ''


class MessageHandler(BaseHandler):
    """Base message handler."""

    update: TGMessageSchema

    async def handle(self) -> None:
        """Handle message."""
        if not self.update.reply_to_message:
            return
        if not self.state.data.message_id == self.update.reply_to_message.message_id:
            return


class CommandHandler(BaseHandler):
    """Base command handler."""

    update: TGMessageSchema

    async def handle(self) -> None:
        """Handle command."""


class CallbackHandler(BaseHandler):
    """Base callback handler."""

    update: TGCallbackQuerySchema

    async def handle(self) -> None:
        """Handle callback."""
        if not self.state.data.message_id == self.update.message.message_id:
            return
