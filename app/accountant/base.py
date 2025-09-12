import json
from typing import Optional, Union

from app import exceptoions
from app.accountant.enums import CallbackHandlerEnum, CommandHadlerEnum, MessageHandlerEnum
from app.accountant.handlers.common import HideCallbackHandler
from app.db_service.models import TGChat, TGUser, TGUserState
from app.db_service.repository import DatabaseAccessor
from app.tg_service import TelegramClient
from app.tg_service.editor import TGMessageEditor
from app.tg_service.schemas import (
    TGCallbackQuerySchema,
    TGChatSchema,
    TGFromSchema,
    TGMessageSchema,
)

from . import handlers
from .handlers import BaseHandler


class Accountant:
    """Accountant logic class."""

    db: DatabaseAccessor
    tg_client: TelegramClient
    editor: TGMessageEditor

    command_handlers = {
        CommandHadlerEnum.CATEGORY_LIST.value: handlers.CategoryListHandler,
        CommandHadlerEnum.CATEGORY_ADD.value: handlers.CategoryAddHandler,
        CommandHadlerEnum.BUDGET_ITEM_ADD.value: handlers.BudgetItemAddHandler,
        CommandHadlerEnum.ENTRY_ADD.value: handlers.EntryAddHandler,
        CommandHadlerEnum.REPORT.value: handlers.ReportHandler,
        CommandHadlerEnum.BALANCE_CREATE.value: handlers.BalanceCreateHandler,
        CommandHadlerEnum.BALANCE_LIST.value: handlers.BalanceListHandler,
        CommandHadlerEnum.BALANCE_SET.value: handlers.BalanceSetHandler,
        CommandHadlerEnum.BALANCE_DELETE.value: handlers.BalanceDeleteHandler,
        CommandHadlerEnum.FOND_CREATE.value: handlers.FondCreateHandler,
        CommandHadlerEnum.FOND_LIST.value: handlers.FondListHandler,
        CommandHadlerEnum.FOND_SET.value: handlers.FondSetHandler,
        CommandHadlerEnum.FOND_DELETE.value: handlers.FondDeleteHandler,
        CommandHadlerEnum.DEBT_CREATE.value: handlers.DebtCreateHandler,
        CommandHadlerEnum.DEBT_LIST.value: handlers.DebtListHandler,
        CommandHadlerEnum.DEBT_SET.value: handlers.DebtSetHandler,
        CommandHadlerEnum.DEBT_DELETE.value: handlers.DebtDeleteHandler,
    }
    callback_handlers = {
        CallbackHandlerEnum.BUDGET_ITEM_ADD_CATEGORY.value: handlers.BudgetItemAddCategoryHandler,
        CallbackHandlerEnum.BUDGET_ITEM_ADD_TYPE.value: handlers.BudgetItemAddTypeHandler,
        CallbackHandlerEnum.ENTRY_ADD_CATEGORY.value: handlers.EntryAddCategoryHandler,
        CallbackHandlerEnum.ENTRY_ADD_BUDGET_ITEM.value: handlers.EntryAddBudgetItemHandler,
        CallbackHandlerEnum.ENTRY_ADD_VALUTE.value: handlers.EntryAddValuteHandler,
        CallbackHandlerEnum.ENTRY_ADD_FINISH.value: handlers.EntryAddFinishHandler,
        CallbackHandlerEnum.REPORT_SELECT_YEAR.value: handlers.ReportSelectYearHandler,
        CallbackHandlerEnum.REPORT_SELECT_MONTH.value: handlers.ReportSelectMonthHandler,
        CallbackHandlerEnum.BALANCE_CREATE_VALUTE.value: handlers.BalanceCreateValuteHandler,
        CallbackHandlerEnum.BALANCE_SET_CHOOSE_ONE.value: handlers.BalanceSetChooseOneHandler,
        CallbackHandlerEnum.BALANCE_DELETE_CHOOSE_ONE.value: handlers.BalanceDeleteChooseOneHandler,
        CallbackHandlerEnum.BALANCE_DELETE_CONFIRM.value: handlers.BalanceDeleteConfirmHandler,
        CallbackHandlerEnum.FOND_CREATE_VALUTE.value: handlers.FondCreateValuteHandler,
        CallbackHandlerEnum.FOND_SET_CHOOSE_ONE.value: handlers.FondSetChooseOneHandler,
        CallbackHandlerEnum.FOND_DELETE_CHOOSE_ONE.value: handlers.FondSetSaveAmountHandler,
        CallbackHandlerEnum.FOND_DELETE_CONFIRM.value: handlers.FondDeleteConfirmHandler,
        CallbackHandlerEnum.DEBT_CREATE_VALUTE.value: handlers.DebtCreateValuteHandler,
        CallbackHandlerEnum.DEBT_SET_CHOOSE_ONE.value: handlers.DebtSetChooseOneHandler,
        CallbackHandlerEnum.DEBT_DELETE_CHOOSE_ONE.value: handlers.DebtSetSaveAmountHandler,
        CallbackHandlerEnum.DEBT_DELETE_CONFIRM.value: handlers.DebtDeleteConfirmHandler,
    }
    message_handlers = {
        MessageHandlerEnum.CATEGORY_ADD_NAME.value: handlers.CategoryAddNameHandler,
        MessageHandlerEnum.BUDGET_ITEM_ADD_NAME.value: handlers.BudgetItemAddNameHandler,
        MessageHandlerEnum.ENTRY_ADD_AMOUNT.value: handlers.EntryAddAmountHandler,
        MessageHandlerEnum.BALANCE_CREATE_NAME.value: handlers.BalanceCreateNameHandler,
        MessageHandlerEnum.BALANCE_SET_SAVE_AMOUNT.value: handlers.BalanceSetSaveAmountHandler,
        MessageHandlerEnum.FOND_CREATE_NAME.value: handlers.FondCreateNameHandler,
        MessageHandlerEnum.FOND_SET_SAVE_AMOUNT.value: handlers.FondSetSaveAmountHandler,
        MessageHandlerEnum.DEBT_CREATE_NAME.value: handlers.DebtCreateNameHandler,
        MessageHandlerEnum.DEBT_SET_SAVE_AMOUNT.value: handlers.DebtSetSaveAmountHandler,
    }
    common_callback_handlers = {
        CallbackHandlerEnum.HIDE.value: HideCallbackHandler,
    }

    def __init__(self, db: DatabaseAccessor, tg_client: TelegramClient, editor: TGMessageEditor):
        """Initialize accountant."""
        self.db = db
        self.tg_client = tg_client
        self.editor = editor

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
