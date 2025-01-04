
from logging import getLogger
from typing import Optional, Protocol, Union

from app.accountant.enums import CallbackHandlerEnum, MessageHandlerEnum
from app.db_service.enums import BudgetItemTypeEnum
from app.db_service.models import BudgetItem, Category, ChatBudgetItem, ChatValute, TGChat, TGUser, TGUserState, Valute
from app.db_service.repository import DatabaseAccessor
from app.tg_service import api as tg_api
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
    TGCallbackQuerySchema,
    TGMessageSchema,
)


CATEGORY_AMOUNT_LIMIT = 12
BUDGET_ITEM_AMOUNT_LIMIT = 12

DEFAULT_VALUTE_CODE = 'RUB'
DEFAULT_VALUTE_NAME = 'Российский рубль'
DEFAULT_VALUTE_SYMBOL = '₽'

ErrorMessage = str
logger = getLogger('app')


class BaseHandler(Protocol):

    db: DatabaseAccessor
    tg: TelegramClient
    editor: TGMessageEditor

    def __init__(
        self,
        db: DatabaseAccessor,
        tg: TelegramClient,
        editor: TGMessageEditor,
    ) -> None:
        super().__init__()
        self.db = db
        self.tg = tg
        self.editor = editor

    async def handle(
        self,
        *,
        chat: TGChat,
        user: TGUser,
        message: TGMessageSchema,
        state: Optional[TGUserState],
    ) -> None:
        pass

    async def send_message(
        self,
        chat: TGChat,
        message: Optional[TGMessageSchema],
        text: str,
        reply_markup: Union[ForceReplySchema, InlineKeyboardMarkup, None] = None,
        is_answer: bool = True,
    ) -> SendTaskSchema:
        reply_parameters: Optional[ReplyParametersRequestSchema] = None
        if is_answer and message:
            reply_parameters = ReplyParametersRequestSchema(
                message_id=message.message_id,
                chat_id=message.chat.tg_id,
            )
        request = SendMessageRequestSchema(
            chat_id=chat.tg_id,
            text=text,
            reply_parameters=reply_parameters,
            reply_markup=reply_markup,
        )
        return await self.tg.send(tg_api.SendMessage, request)

    async def delete_message(self, message: TGMessageSchema) -> SendTaskSchema:
        request = DeleteMessageRequestSchema(
            chat_id=message.chat.tg_id, message_id=message.message_id,
        )
        return await self.tg.send(tg_api.DeleteMessage, request)

    async def edit_message(
        self,
        chat_tg_id: int,
        message_tg_id: int,
        text: str,
        reply_markup: Union[ForceReplySchema, InlineKeyboardMarkup, None] = None
    ) -> SendTaskSchema:
        request = EditMessageTextRequestSchema(
            chat_id=chat_tg_id,
            message_id=message_tg_id,
            text=text,
            reply_markup=reply_markup,
        )
        return await self.tg.send(tg_api.EditMessageText, request)

    async def edit_message_reply_markup(
        self,
        message: TGMessageSchema,
        reply_markup: Union[ForceReplySchema, InlineKeyboardMarkup, None] = None
    ) -> SendTaskSchema:
        request = EditMessageReplyMarkupRequestSchema(
            chat_id=message.chat.tg_id,
            message_id=message.message_id,
            reply_markup=reply_markup,
        )
        return await self.tg.send(tg_api.EditMessageReplyMarkup, request)

    async def set_state(
        self,
        user: TGUser,
        state: Optional[TGUserState],
        state_name: Union[MessageHandlerEnum, CallbackHandlerEnum],
        data_raw: dict,
    ) -> TGUserState:
        if not state:
            state = TGUserState(
                tg_user_id=user.id,
                state=state_name.value,
                data_raw=data_raw,
            )
            await self.db.state_repo.create_item(state)
        else:
            state.state = state_name.value
            state.data_raw = data_raw
            await self.db.state_repo.update_item(state)
        return state

    async def get_or_create_budget_item(self, name: str, type: BudgetItemTypeEnum) -> BudgetItem:
        if not (budget_item := await self.db.budget_item_repo.get_by_name_type(name=name, type=type)):
            budget_item = BudgetItem(name=name, type=type.value)
            budget_item = await self.db.budget_item_repo.create_item(budget_item)
        return budget_item

    async def get_chat_valutes(self, chat: TGChat) -> list[Valute]:
        valutes = chat.valutes
        if not valutes:
            rub_valute = await self.db.valute_repo.get_by_code(code=DEFAULT_VALUTE_CODE)
            if not rub_valute:
                rub_valute = await self.db.valute_repo.create_item(
                    Valute(
                        name=DEFAULT_VALUTE_NAME,
                        symbol=DEFAULT_VALUTE_SYMBOL,
                        code=DEFAULT_VALUTE_CODE,
                    )
                )
            chat_valute = ChatValute(chat_id=chat.id, valute_id=rub_valute.id)
            chat.valutes = [rub_valute]
            await self.db.chat_valute_repo.create_item(chat_valute)
        return chat.valutes

    def get_selected_category(self, chat: TGChat, callback: TGCallbackQuerySchema) -> Category:
        category: Optional[Category] = None
        category_name = callback.data
        if not (category := [c for c in chat.categories if c.name == category_name]):
            raise RuntimeError('selected category not found')
        else:
            category = category[0]
        return category

    def get_state_category(self, chat: TGChat, state: Optional[TGUserState]) -> Category:
        category: Optional[Category] = None
        error: Optional[str] = None
        if not state:
            error = 'state not found'
        elif not (category_id := state.data.category_id):
            error = 'state category_id not found'
        elif not (category := [c for c in chat.categories if c.id == category_id]):
            error = 'state category not found'
        else:
            category = category[0]
        if error:
            raise RuntimeError(error)
        return category

    def get_selected_budget_item(
        self,
        chat: TGChat,
        state: Optional[TGUserState],
        callback: TGCallbackQuerySchema,
    ) -> BudgetItem:
        budget_item: Optional[BudgetItem] = None
        budget_item_id = int(callback.data)
        category = self.get_state_category(chat, state)
        if not (budget_item := [b for b in category.budget_items if b.id == budget_item_id]):
            raise RuntimeError('selected budget item not found')
        else:
            budget_item = budget_item[0]
        return budget_item

    def get_state_budget_item(
        self,
        chat: TGChat,
        state: Optional[TGUserState],
    ) -> tuple[Category, BudgetItem]:
        budget_item: Optional[BudgetItem] = None
        error: Optional[str] = None
        category = self.get_state_category(chat, state)
        if not category:
            error = 'state category not found'
        elif not (budget_item_id := state.data.budget_item_id):
            error = 'state budget_item_id not found'
        elif not (budget_item := [b for b in category.budget_items if b.id == budget_item_id]):
            error = 'state budget_item not found'
        else:
            budget_item = budget_item[0]
        if error:
            raise RuntimeError(error)
        return category, budget_item

    def get_selected_valute(
        self,
        chat: TGChat,
        callback: TGCallbackQuerySchema,
    ) -> Valute:
        valute: Optional[Valute] = None
        valute_code = callback.data
        if not (valute := [v for v in chat.valutes if v.code == valute_code]):
            raise RuntimeError('selected valute not found')
        else:
            valute = valute[0]
        return valute

    def get_state_valute(self, chat: TGChat, state: Optional[TGUserState]) -> Valute:
        valute: Optional[Valute] = None
        error: Optional[str] = None
        if not state:
            error = 'state not found'
        elif not (valute_id := state.data.valute_id):
            error = 'state valute_id not found'
        elif not (valute := [v for v in chat.valutes if v.id == valute_id]):
            error = 'state valute not found'
        else:
            valute = valute[0]
        if error:
            raise RuntimeError(error)
        return valute

    async def get_state_chat_budget_item(self, chat: TGChat, state: Optional[TGUserState]) -> ChatBudgetItem:
        chat_budget_item: Optional[ChatBudgetItem] = None
        error: Optional[str] = None
        if not state:
            error = 'state not found'
        elif not (category_id := state.data.category_id):
            error = 'state category_id not found'
        elif not (budget_item_id := state.data.budget_item_id):
            error = 'state budget_item_id not found'
        elif not (chat_budget_item := await self.db.chat_budget_item_repo.get_chat_budget_item(
            chat_id=chat.id, category_id=category_id, budget_item_id=budget_item_id,
        )):
            error = 'state chat_budget_item not found'
        if error:
            raise RuntimeError(error)
        return chat_budget_item

    def add_name_emoji(self, name: str) -> str:
        return self.editor.add_name_emoji(name)

    async def get_message_entries_line(self, message_id: int) -> Optional[str]:
        data_rows = await self.db.entry_repo.get_message_entries(message_id=message_id)
        if not data_rows:
            return None

        lines = []
        category_length = max(len(row[0].name) for row in data_rows)
        budget_item_length = max(len(row[1].name) for row in data_rows)
        for category, budget_item, entry, valute in data_rows:
            line = self.editor.make_entry_line(
                category_name=category.name,
                budget_item_name=budget_item.name,
                budget_item_type=budget_item.type,
                amount=entry.amount,
                valute_code=valute.code,
                category_name_length=category_length,
                budget_item_length=budget_item_length,
            )
            lines.append(line)
        return '\n'.join(lines)


class MessageHandler(BaseHandler):

    async def handle(
        self,
        *,
        message: TGMessageSchema,
        state: TGUserState | None,
        **_,
    ) -> None:
        if not self._validate_answer_message_id(message, state):
            return

    @staticmethod
    def _validate_answer_message_id(
        message: TGMessageSchema,
        state: Optional[TGUserState],
    ) -> bool:
        if not state:
            return False
        elif not message.reply_to_message:
            return False
        return state.data.message_id == message.reply_to_message.message_id


class CommandHandler(BaseHandler):
    pass


class CallbackHandler(BaseHandler):
    @staticmethod
    def _validate_callback_message_id(
        message: TGMessageSchema, state: Optional[TGUserState],
    ) -> bool:
        if not state:
            return False
        return state.data.message_id == message.message_id

    async def handle(
        self,
        *,
        callback: TGCallbackQuerySchema,
        state: Optional[TGUserState],
        **_,
    ):
        if not self._validate_callback_message_id(callback.message, state):
            return
