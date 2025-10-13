import json
from typing import Optional, Type, Union

from app import exceptoions
from app.accountant.enums import CallbackHandlerEnum, MessageHandlerEnum
from app.db_service.models import TGChat, TGUser, TGUserState
from app.db_service.repository import DatabaseAccessor
from app.tg_service import TelegramClient
from app.tg_service.editor import TGMessageEditor
from app.tg_service.schemas import TGCallbackQuerySchema, TGChatSchema, TGFromSchema, TGMessageSchema

from .handlers import BaseHandler


class Accountant:
    """Accountant logic class."""

    db: DatabaseAccessor
    tg_client: TelegramClient
    editor: TGMessageEditor
    command_handlers: dict[str, BaseHandler]
    callback_handlers: dict[str, BaseHandler]
    message_handlers: dict[str, BaseHandler]
    common_callback_handlers: dict[str, BaseHandler]

    def __init__(self, db: DatabaseAccessor, tg_client: TelegramClient, editor: TGMessageEditor,
                 command_handlers: dict[str, Type[BaseHandler]],
                 callback_handlers: dict[str, Type[BaseHandler]],
                 message_handlers: dict[str, Type[BaseHandler]],
                 common_callback_handlers: dict[str, Type[BaseHandler]]):
        """Initialize accountant."""
        self.db = db
        self.tg_client = tg_client
        self.editor = editor
        self.command_handlers = command_handlers
        self.callback_handlers = callback_handlers
        self.message_handlers = message_handlers
        self.common_callback_handlers = common_callback_handlers

    @exceptoions.catch_exception
    async def process_message(self, update: Union[TGMessageSchema, TGCallbackQuerySchema]):
        """Process Telegram update."""
        is_message = isinstance(update, TGMessageSchema)
        chat_schema = update.chat if is_message else update.message.chat
        chat = await self._get_or_create_chat(chat_schema)
        user = await self._get_or_create_user(update.msg_from)
        state = await self._get_or_create_state(user)
        process_payload = {
            'tg': self.tg_client, 'db': self.db, 'editor': self.editor,
            'chat': chat, 'user': user, 'update': update, 'state': state}

        handler: Optional[BaseHandler] = None
        if is_message and update.command:
            handler = await self._process_command(**process_payload)
        elif not is_message and 'common_action' in update.data:
            handler = await self._process_common_callback(**process_payload)
        elif not is_message:
            handler = await self._process_callback(**process_payload)
        else:
            handler = await self._process_message(**process_payload)
        if handler:
            await handler.handle()

    async def _process_command(
            self, update: TGMessageSchema, **process_payload) -> Optional[BaseHandler]:
        """Process command."""
        handler = self.command_handlers.get(update.command)
        return handler(update=update, **process_payload) if handler else None

    async def _process_callback(
            self, state: Optional[TGUserState], **process_payload) -> Optional[BaseHandler]:
        """Process callback."""
        if not state:
            return
        if state.name not in list(CallbackHandlerEnum):
            return
        handler = self.callback_handlers.get(CallbackHandlerEnum(state.name))
        return handler(state=state, **process_payload) if handler else None

    async def _process_common_callback(
            self, update: TGCallbackQuerySchema, **process_payload) -> Optional[BaseHandler]:
        """Process common callback."""
        request = json.loads(update.data)
        update.data = request
        handler = self.common_callback_handlers.get(request['common_action'])
        return handler(update=update, **process_payload) if handler else None

    async def _process_message(
            self, state: Optional[TGUserState], **process_payload) -> Optional[BaseHandler]:
        """Process message."""
        if not state:
            return
        if state.name not in list(MessageHandlerEnum):
            return
        handler = self.message_handlers.get(MessageHandlerEnum(state.name))
        return handler(state=state, **process_payload) if handler else None

    async def _get_or_create_chat(self, chat_schema: TGChatSchema) -> TGChat:
        """Get or create chat."""
        if not (chat := await self.db.chat_repo.get_by_tg_id(chat_schema.tg_id)):
            data = chat_schema.model_dump(include={'tg_id', 'type', 'title'})
            chat = TGChat(**data)
            chat = await self.db.chat_repo.create_item(chat)

        return chat

    async def _get_or_create_user(self, user_schema: TGFromSchema) -> TGUser:
        """Get or create user."""
        if not (user := await self.db.user_repo.get_by_tg_id(user_schema.tg_id)):
            data = user_schema.model_dump(
                include={'tg_id', 'is_bot', 'first_name', 'username', 'language_code'},
            )
            user = TGUser(**data)
            user = await self.db.user_repo.create_item(user)

        return user

    async def _get_or_create_state(self, user: TGUser) -> TGUserState:
        """Get or create state."""
        if not (state := await self.db.state_repo.get_tg_user_state(user.id)):
            state = TGUserState(
                tg_user_id=user.id, name=MessageHandlerEnum.DEFAULT.value, data_raw={})
            state = await self.db.state_repo.create_item(state)

        return state
