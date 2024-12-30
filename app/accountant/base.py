from logging import getLogger
from typing import Optional, Union

from app.accountant.enums import CallbackHandlerEnum, CommandHadlerEnum, MessageHandlerEnum
from app.accountant.handlers.common import HideCallbackHandler
from app.db_service.models import TGChat, TGUser, TGUserState
from app.db_service.repository import DatabaseAccessor
from app.tg_service import TelegramClient
from app.tg_service.editor import TGMessageEditor
from app.tg_service.schemas import TGCallbackQuerySchema, TGChatSchema, TGFromSchema, TGMessageSchema

from .handlers import (
    BaseHandler,
    BudgetItemAddCategoryHandler,
    BudgetItemAddHandler,
    BudgetItemAddNameHandler,
    BudgetItemAddTypeHandler,
    CategoryAddHandler,
    CategoryAddNameHandler,
    CategoryListHandler,
    EntryAddAmountHandler,
    EntryAddBudgetItemHandler,
    EntryAddCategoryHandler,
    EntryAddFinishHandler,
    EntryAddHandler,
    EntryAddValuteHandler,
    ReportHandler,
    ReportSelectMonthHandler,
    ReportSelectYearHandler,
)


logger = getLogger('app')


class Accountant:
    db: DatabaseAccessor
    tg_client: TelegramClient
    editor: TGMessageEditor
    # rq: QueueManager

    command_handlers = {
        CommandHadlerEnum.CATEGORY_LIST.value: CategoryListHandler,
        CommandHadlerEnum.CATEGORY_ADD.value: CategoryAddHandler,
        CommandHadlerEnum.BUDGET_ITEM_ADD.value: BudgetItemAddHandler,
        CommandHadlerEnum.ENTRY_ADD.value: EntryAddHandler,
        CommandHadlerEnum.REPORT.value: ReportHandler,
    }
    callback_handlers = {
        CallbackHandlerEnum.BUDGET_ITEM_ADD_CATEGORY.value: BudgetItemAddCategoryHandler,
        CallbackHandlerEnum.BUDGET_ITEM_ADD_TYPE.value: BudgetItemAddTypeHandler,
        CallbackHandlerEnum.ENTRY_ADD_CATEGORY.value: EntryAddCategoryHandler,
        CallbackHandlerEnum.ENTRY_ADD_BUDGET_ITEM.value: EntryAddBudgetItemHandler,
        CallbackHandlerEnum.ENTRY_ADD_VALUTE.value: EntryAddValuteHandler,
        CallbackHandlerEnum.ENTRY_ADD_FINISH.value: EntryAddFinishHandler,
        CallbackHandlerEnum.REPORT_SELECT_YEAR.value: ReportSelectYearHandler,
        CallbackHandlerEnum.REPORT_SELECT_MONTH.value: ReportSelectMonthHandler,
        CallbackHandlerEnum.HIDE.value: HideCallbackHandler,

    }
    message_handlers = {
        MessageHandlerEnum.CATEGORY_ADD_NAME.value: CategoryAddNameHandler,
        MessageHandlerEnum.BUDGET_ITEM_ADD_NAME.value: BudgetItemAddNameHandler,
        MessageHandlerEnum.ENTRY_ADD_AMOUNT.value: EntryAddAmountHandler,
    }

    def __init__(self, db: DatabaseAccessor, tg_client: TelegramClient, editor: TGMessageEditor):

        self.db = db
        self.tg_client = tg_client
        self.editor = editor

    async def process_message(self, update: Union[TGMessageSchema, TGCallbackQuerySchema]):
        is_message = isinstance(update, TGMessageSchema)
        chat_schema = update.chat if is_message else update.message.chat
        chat = await self._get_or_create_chat(chat_schema)
        user = await self._get_or_create_user(update.msg_from)
        state = await self._get_or_create_state(user)
        try:
            if is_message and update.command:
                await self._process_command(chat, user, update, state)
            elif not is_message and update.data == 'hide':
                await self._process_hide_callback(chat, user, update, state)
            elif not is_message:
                await self._process_callback(chat, user, update, state)
            else:
                await self._process_message(chat, user, update, state)
        except Exception as error:
            known_errors = (
                RuntimeError,
                ValueError,
            )
            level = logger.error if isinstance(error, known_errors) else logger.exception
            level(
                'chat[%s] user[%s] update %s is_message %s error %s',
                chat.id, user.id, update, is_message, error,
            )

    async def _process_command(
        self,
        chat: TGChat,
        user: TGUser,
        message: TGMessageSchema,
        state: Optional[TGUserState]
    ):
        handler = self.command_handlers.get(message.command)
        if handler:
            handler = handler(self.db, self.tg_client, self.editor)
            await handler.handle(chat=chat, user=user, message=message, state=state)

    async def _process_callback(
        self,
        chat: TGChat,
        user: TGUser,
        callback: TGCallbackQuerySchema,
        state: Optional[TGUserState],
    ):
        handler: Optional[BaseHandler] = None
        if not state:
            return
        elif state.state not in list(CallbackHandlerEnum):
            return
        else:
            state_enum = CallbackHandlerEnum(state.state)
            handler = self.callback_handlers.get(state_enum)
        if handler:
            handler = handler(self.db, self.tg_client, self.editor)
            await handler.handle(chat=chat, user=user, callback=callback, state=state)

    async def _process_hide_callback(
        self,
        chat: TGChat,
        user: TGUser,
        callback: TGCallbackQuerySchema,
        state: Optional[TGUserState],
    ):
        handler = HideCallbackHandler(self.db, self.tg_client, self.editor)
        await handler.handle(chat=chat, user=user, callback=callback, state=state)

    async def _process_message(
        self,
        chat: TGChat,
        user: TGUser,
        message: TGMessageSchema,
        state: Optional[TGUserState],
    ):
        handler: Optional[BaseHandler] = None
        if not state:
            return
        if state.state not in list(MessageHandlerEnum):
            return
        else:
            state_enum = MessageHandlerEnum(state.state)
            handler = self.message_handlers.get(state_enum)
        if handler:
            handler = handler(self.db, self.tg_client, self.editor)
            await handler.handle(chat=chat, user=user, message=message, state=state)

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

    async def _get_or_create_state(self, user: TGUser) -> TGUserState:
        if not (state := await self.db.state_repo.get_tg_user_state(user.id)):
            state = TGUserState(user_id=user.id, state=MessageHandlerEnum.DEFAULT.value, data_raw={})
            state = await self.db.state_repo.create_item(state)

        return state
