
from logging import getLogger
from typing import Optional, Protocol, Union

from app.accountant.enums import CallbackHandlerEnum, DecisionEnum, MessageHandlerEnum
from app.accountant.messages import (
    BUDGET_ITEM_ADD_CATEGORY,
    BUDGET_ITEM_ADD_EXISTS_ERROR,
    BUDGET_ITEM_ADD_LIMIT_ERROR,
    BUDGET_ITEM_ADD_NAME,
    BUDGET_ITEM_ADD_NAME_PLACEHOLDER,
    BUDGET_ITEM_ADD_TYPE,
    BUDGET_ITEM_ADDED,
    CATEGORY_CREATED,
    CATEGORY_ENTER_NEW,
    CATEGORY_ENTER_NEW_PLACEHOLDER,
    CATEGORY_EXISTS_ERROR,
    CATEGORY_LIMIT_ERROR,
    ENTRY_ADD_ADDED,
    ENTRY_ADD_AMOUNT_ERROR,
    ENTRY_ADD_AMOUNT_MAIN,
    ENTRY_ADD_AMOUNT_PLACEHOLDER,
    ENTRY_ADD_AMOUNT_SECONDARY,
    ENTRY_ADD_BUDGET_ITEM,
    ENTRY_ADD_CATEGORY,
    ENTRY_ADD_FINISH,
    ENTRY_ADD_NO_BUDGET_ITEMS_ERROR,
    ENTRY_ADD_VALUTE,
    NO_CATEGORIES,
)
from app.db_service.enums import BudgetItemTypeEnum
from app.db_service.models import (
    BudgetItem,
    Category,
    ChatBudgetItem,
    ChatValute,
    Entry,
    TGChat,
    TGUser,
    TGUserState,
    Valute,
)
from app.db_service.repository import DatabaseAccessor
from app.db_service.schemas import StateDataSchema
from app.tg_service import api as tg_api
from app.tg_service.client import SendTaskSchema, TelegramClient
from app.tg_service.editor import TGMessageEditor
from app.tg_service.schemas import (
    DeleteMessageRequestSchema,
    EditMessageReplyMarkupRequestSchema,
    EditMessageTextRequestSchema,
    EditMessageTextResponseSchema,
    ForceReplySchema,
    InlineKeyboardMarkup,
    ReplyParametersRequestSchema,
    SendMessageRequestSchema,
    SendMessageResponseSchema,
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
        budget_item_name = callback.data
        category = self.get_state_category(chat, state)
        if not (budget_item := [b for b in category.budget_items if b.name == budget_item_name]):
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


class CategoryListHandler(CommandHandler):
    async def handle(
        self,
        *,
        chat: TGChat,
        message: TGMessageSchema,
        **_,
    ) -> None:
        await self.delete_message(message)
        if chat.categories:
            text = self.editor.make_category_list(chat.categories)
        else:
            text = text or NO_CATEGORIES
        await self.send_message(chat, message, text)


class CategoryAddHandler(CommandHandler):
    async def handle(
        self,
        *,
        chat: TGChat,
        message: TGMessageSchema,
        user: TGUser,
        state: Optional[TGUserState],
        **_,
    ) -> None:
        await self.delete_message(message)
        if len(chat.categories) >= CATEGORY_AMOUNT_LIMIT:
            text = CATEGORY_LIMIT_ERROR.format(CATEGORY_AMOUNT_LIMIT)
            keyboard = None
        else:
            mention = self.editor.get_mention(user.username)
            text = CATEGORY_ENTER_NEW.format(mention)
            keyboard = ForceReplySchema(
                input_field_placeholder=CATEGORY_ENTER_NEW_PLACEHOLDER,
            )
        task = await self.send_message(chat, message, text, keyboard, False)
        await task.event.wait()
        response: Optional[SendMessageResponseSchema] = task.response
        if response:
            data_raw = dict(message_id=response.result.message_id)
            await self.set_state(user, state, MessageHandlerEnum.CATEGORY_ADD_NAME, data_raw)


class CategoryAddNameHandler(MessageHandler):
    async def handle(
        self,
        *,
        chat: TGChat,
        message: TGMessageSchema,
        user: TGUser,
        state: Optional[TGUserState],
        **_,
    ) -> None:
        await self.delete_message(message)
        await super().handle(user=user, message=message, state=state, **_)
        categories = chat.categories
        new_name = message.text.strip().lower()
        is_exists = bool([c.name for c in categories if c.name == new_name])
        if is_exists:
            text = CATEGORY_EXISTS_ERROR.format(new_name)
        else:
            category = Category(name=new_name)
            chat.categories.append(category)
            await self.db.chat_repo.update_item(chat)
            text = CATEGORY_CREATED.format(new_name)
        await self.send_message(chat, message, text, False)
        await self.set_state(user, state, MessageHandlerEnum.DEFAULT, {})


class BudgetItemAddHandler(CommandHandler):

    async def handle(
        self,
        *,
        chat: TGChat,
        message: TGMessageSchema,
        user: TGUser,
        state: Optional[TGUserState],
        **_,
    ) -> None:
        await self.delete_message(message)
        keyboard = self.editor.get_category_keyboard(chat.categories)
        task = await self.send_message(chat, message, BUDGET_ITEM_ADD_CATEGORY, keyboard, is_answer=False)
        await task.event.wait()
        response: Optional[SendMessageResponseSchema] = task.response
        if response:
            data_raw = dict(message_id=response.result.message_id)
            await self.set_state(user, state, CallbackHandlerEnum.BUDGET_ITEM_ADD_CATEGORY, data_raw)


class BudgetItemAddCategoryHandler(CallbackHandler):

    async def handle(
        self,
        *,
        chat: TGChat,
        callback: TGCallbackQuerySchema,
        user: TGUser,
        state: Optional[TGUserState],
        **_,
    ) -> None:
        if not self._validate_callback_message_id(callback.message, state):
            return
        if not (category := self.get_selected_category(chat, callback)):
            return
        if len(category.budget_items) >= BUDGET_ITEM_AMOUNT_LIMIT:
            text = BUDGET_ITEM_ADD_LIMIT_ERROR.format(category.name, BUDGET_ITEM_AMOUNT_LIMIT)
            keyboard = self.editor.get_category_keyboard(chat.categories)
            await self.edit_message(chat.tg_id, callback.message.message_id, text, keyboard)
        else:
            text = BUDGET_ITEM_ADD_TYPE
            keyboard = self.editor.get_budget_item_type_keyboard()
            edit_task = await self.edit_message(chat.tg_id, callback.message.message_id, text, keyboard)
            await edit_task.event.wait()
            response: Optional[EditMessageTextResponseSchema] = edit_task.response
            if response:
                data_raw = dict(
                    message_id=callback.message.message_id,
                    category_id=category.id,
                )
                await self.set_state(user, state, CallbackHandlerEnum.BUDGET_ITEM_ADD_TYPE, data_raw)


class BudgetItemAddTypeHandler(CallbackHandler):

    async def handle(
        self,
        *,
        chat: TGChat,
        callback: TGCallbackQuerySchema,
        user: TGUser,
        state: Optional[TGUserState],
        **_,
    ) -> None:
        if not self._validate_callback_message_id(callback.message, state):
            return
        try:
            _type = BudgetItemTypeEnum(callback.data)
        except Exception as error:
            logger.error('%s-E %s', self.__class__.__name__, error)
            return
        category = await self.db.category_repo.get_by_id(state.data.category_id)
        category_name = category.name if category else ''
        mention = self.editor.get_mention(user.username)
        text = BUDGET_ITEM_ADD_NAME.format(category_name, _type.value, mention or '')
        keyboard = ForceReplySchema(input_field_placeholder=BUDGET_ITEM_ADD_NAME_PLACEHOLDER)
        send_task = await self.send_message(chat, callback.message, text, reply_markup=keyboard)
        await send_task.event.wait()
        response: Optional[SendMessageResponseSchema] = send_task.response
        if response:
            await self.delete_message(callback.message)
            data_raw = dict(
                message_id=response.result.message_id,
                category_id=category.id,
                budget_item_type=_type.value,
            )
            await self.set_state(user, state, MessageHandlerEnum.BUDGET_ITEM_ADD_NAME, data_raw)


class BudgetItemAddNameHandler(MessageHandler):

    async def handle(
        self,
        *,
        chat: TGChat,
        message: TGMessageSchema,
        user: TGUser,
        state: Optional[TGUserState],
        **_,
    ) -> None:
        await super().handle(user=user, message=message, state=state, **_)
        category = await self.db.category_repo.get_by_id(state.data.category_id)
        new_name = message.text.strip().lower()
        type = BudgetItemTypeEnum(state.data.budget_item_type)
        if await self.db.chat_budget_item_repo.get_chat_budget_item(
            chat_id=chat.id,
            category_id=state.data.category_id,
            budget_item_name=new_name,
            budget_item_type=type,
        ):
            mention = self.editor.get_mention(user.username)
            text = BUDGET_ITEM_ADD_EXISTS_ERROR.format(category.name, new_name, type.value, mention or '')
            keyboard = ForceReplySchema(input_field_placeholder=BUDGET_ITEM_ADD_NAME_PLACEHOLDER)
            send_task = await self.send_message(chat, message, text, reply_markup=keyboard)
            await send_task.event.wait()
            response: Optional[SendMessageResponseSchema] = send_task.response
            if response:
                await self.delete_message(message.reply_to_message)
                await self.delete_message(message)
                state.data_raw['message_id'] = response.result.message_id
                await self.set_state(user, state, MessageHandlerEnum.BUDGET_ITEM_ADD_NAME, state.data_raw)
        else:
            budget_item = await self.get_or_create_budget_item(new_name, type)
            if (chat_budget_item := await self.db.chat_budget_item_repo.get_no_budget_item_row(
                chat_id=chat.id, category_id=category.id,
            )):
                chat_budget_item.budget_item_id = budget_item.id
                await self.db.chat_budget_item_repo.update_item(chat_budget_item)
            else:
                chat_budget_item = ChatBudgetItem(
                    chat_id=chat.id,
                    category_id=state.data.category_id,
                    budget_item_id=budget_item.id,
                )
                await self.db.chat_budget_item_repo.create_item(chat_budget_item)
            text = BUDGET_ITEM_ADDED.format(new_name, type.value)
            await self.delete_message(message.reply_to_message)
            await self.delete_message(message)
            await self.send_message(chat, message, text)
            await self.set_state(user, state, MessageHandlerEnum.DEFAULT, {})


class EntryAddHandler(CommandHandler):
    async def handle(
        self,
        *,
        chat: TGChat,
        message: TGMessageSchema,
        user: TGUser,
        state: Optional[TGUserState],
        **_,
    ) -> None:
        await self.delete_message(message)
        keyboard = self.editor.get_category_keyboard(chat.categories)
        task = await self.send_message(chat, message, ENTRY_ADD_CATEGORY, keyboard, is_answer=False)
        await task.event.wait()
        response: Optional[SendMessageResponseSchema] = task.response
        if response:
            data_raw = dict(message_id=response.result.message_id)
            await self.set_state(user, state, CallbackHandlerEnum.ENTRY_ADD_CATEGORY, data_raw)


class EntryAddCategoryHandler(CallbackHandler):

    async def handle(
        self,
        *,
        chat: TGChat,
        callback: TGCallbackQuerySchema,
        user: TGUser,
        state: Optional[TGUserState],
        **_,
    ) -> None:
        if not self._validate_callback_message_id(callback.message, state):
            return
        if not (category := self.get_selected_category(chat, callback)):
            return
        if not category.budget_items:
            text = ENTRY_ADD_NO_BUDGET_ITEMS_ERROR.format(category.name)
            keyboard = self.editor.get_category_keyboard(chat.categories)
            await self.edit_message(chat.tg_id, callback.message.message_id, text, keyboard)
        else:
            keyboard = self.editor.get_budget_item_keyboard(category.budget_items)
            text = ENTRY_ADD_BUDGET_ITEM.format(category.name)
            text = self.editor.add_state_entries_lines(text, state.data.entries)
            task = await self.edit_message(chat.tg_id, callback.message.message_id, text, keyboard)
            await task.event.wait()
            response: Optional[EditMessageTextResponseSchema] = task.response
            if response:
                data_raw = state.data_raw
                data_raw['category_id'] = category.id
                await self.set_state(user, state, CallbackHandlerEnum.ENTRY_ADD_BUDGET_ITEM, data_raw)


class EntryAddBudgetItemHandler(CallbackHandler):
    async def handle(
        self,
        *,
        user: TGUser,
        chat: TGChat,
        callback: TGCallbackQuerySchema,
        state: TGUserState | None,
        **_,
    ) -> None:
        await super().handle(callback=callback, state=state, **_)
        category = self.get_state_category(chat=chat, state=state)
        budget_item = self.get_selected_budget_item(chat=chat, state=state, callback=callback)
        valutes = await self.get_chat_valutes(chat=chat)
        keyboard = self.editor.get_valute_keyboard(valutes)
        text = ENTRY_ADD_VALUTE.format(category.name, budget_item.name)
        text = self.editor.add_state_entries_lines(text, state.data.entries)
        task = await self.edit_message(chat.tg_id, callback.message.message_id, text, keyboard)
        await task.event.wait()
        response: Optional[EditMessageTextResponseSchema] = task.response
        if response:
            data_raw = state.data_raw
            data_raw['budget_item_id'] = budget_item.id
            await self.set_state(user, state, CallbackHandlerEnum.ENTRY_ADD_VALUTE, data_raw)


class EntryAddValuteHandler(CallbackHandler):
    async def handle(
        self,
        *,
        chat: TGChat,
        callback: TGCallbackQuerySchema,
        user: TGUser,
        state: Optional[TGUserState],
        **_,
    ) -> None:
        await super().handle(callback=callback, state=state, **_)
        category, budget_item = self.get_state_budget_item(chat=chat, state=state)
        valute = self.get_selected_valute(chat=chat, callback=callback)
        text = ENTRY_ADD_AMOUNT_MAIN.format(category.name, budget_item.name, valute.code)
        text = self.editor.add_state_entries_lines(text, state.data.entries)
        keyboard = ForceReplySchema(input_field_placeholder=ENTRY_ADD_AMOUNT_PLACEHOLDER)
        await self.edit_message(chat.tg_id, callback.message.message_id, text)

        mention = self.editor.get_mention(user.username)
        text = ENTRY_ADD_AMOUNT_SECONDARY.format(mention or '')
        task = await self.send_message(chat, None, text, keyboard, is_answer=False)
        await task.event.wait()
        response: Optional[SendMessageResponseSchema] = task.response
        if response:
            data_raw = state.data_raw
            data_raw['valute_id'] = valute.id
            data_raw['message_id'] = response.result.message_id
            data_raw['main_message_id'] = callback.message.message_id
            await self.set_state(user, state, MessageHandlerEnum.ENTRY_ADD_AMOUNT, data_raw)


class EntryAddAmountHandler(MessageHandler):
    async def handle(
        self,
        *,
        chat: TGChat,
        message: TGMessageSchema,
        user: TGUser,
        state: Optional[TGUserState],
        **_,
    ) -> None:
        await super().handle(user=user, message=message, state=state, **_)
        await self.delete_message(message)
        if message.reply_to_message:
            await self.delete_message(message.reply_to_message)
        amount: Optional[float] = None
        inputed = message.text.strip()
        try:
            amount = float(message.text.strip())
        except ValueError:
            pass
        if not amount:
            mention = self.editor.get_mention(user.username)
            text = ENTRY_ADD_AMOUNT_ERROR.format(inputed)
            text += '\n' + ENTRY_ADD_AMOUNT_SECONDARY.format(mention or '')
            keyboard = ForceReplySchema(input_field_placeholder=ENTRY_ADD_AMOUNT_PLACEHOLDER)
            task = await self.send_message(chat, None, text, keyboard, is_answer=False)
            await task.event.wait()
            response: Optional[SendMessageResponseSchema] = task.response
            if response:
                data_raw = state.data_raw
                data_raw['message_id'] = response.result.message_id
                await self.set_state(user, state, MessageHandlerEnum.ENTRY_ADD_AMOUNT, data_raw)
        else:
            category, budget_item = self.get_state_budget_item(chat=chat, state=state)
            chat_budget_item = await self.get_state_chat_budget_item(chat=chat, state=state)
            valute = self.get_state_valute(chat=chat, state=state)
            entry = Entry(
                chat_budget_item_id=chat_budget_item.id,
                valute_id=valute.id,
                amount=amount,
                data_raw=dict(message_id=state.data.main_message_id),
            )
            await self.db.entry_repo.create_item(entry)
            entry_data = dict(
                category_name=category.name,
                budget_item_name=budget_item.name,
                valute_code=valute.code,
                amount=amount,
            )
            data_raw = dict(
                message_id=state.data.main_message_id,
                entries=state.data.entries + [entry_data],
            )
            state.data = StateDataSchema.model_validate(data_raw)
            await self.set_state(user, state, CallbackHandlerEnum.ENTRY_ADD_FINISH, state.data.model_dump())
            keyboard = self.editor.get_finish_keyboard(chat.categories)
            text = ENTRY_ADD_ADDED
            text = self.editor.add_state_entries_lines(text, state.data.entries)
            await self.edit_message(chat.tg_id, state.data.message_id, text, keyboard)


class EntryAddFinishHandler(CallbackHandler):
    async def handle(
        self,
        *,
        chat: TGChat,
        callback: TGCallbackQuerySchema,
        user: TGUser,
        state: Optional[TGUserState],
        **_,
    ) -> None:
        await super().handle(callback=callback, state=state, **_)
        decision = callback.data
        if decision == DecisionEnum.FINISH:
            text = ENTRY_ADD_FINISH
            text = self.editor.add_state_entries_lines(text, state.data.entries)
            await self.set_state(user, state, MessageHandlerEnum.DEFAULT, {})
            await self.edit_message(chat.tg_id, callback.message.message_id, text)
        elif decision == DecisionEnum.MORE:
            await self.set_state(user, state, CallbackHandlerEnum.ENTRY_ADD_CATEGORY, state.data_raw)
            text = ENTRY_ADD_CATEGORY
            text = self.editor.add_state_entries_lines(text, state.data.entries)
            keyboard = self.editor.get_category_keyboard(chat.categories)
            await self.edit_message(chat.tg_id, callback.message.message_id, text, keyboard)
