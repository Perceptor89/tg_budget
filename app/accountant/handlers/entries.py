from typing import Optional

from app import exceptoions
from app.accountant.enums import CallbackHandlerEnum, DecisionEnum, MessageHandlerEnum
from app.accountant.messages import (
    ENTRY_ADD_ADDED,
    ENTRY_ADD_AMOUNT,
    ENTRY_ADD_AMOUNT_ERROR,
    ENTRY_ADD_AMOUNT_PLACEHOLDER,
    ENTRY_ADD_BUDGET_ITEM,
    ENTRY_ADD_CATEGORY,
    ENTRY_ADD_FINISH,
    ENTRY_ADD_NO_BUDGET_ITEMS_ERROR,
    ENTRY_ADD_VALUTE,
)
from app.db_service.models import BudgetItem, Category, ChatBudgetItem, Entry, TGChat, TGUserState
from app.db_service.repository import DatabaseAccessor
from app.tg_service.editor import TGMessageEditor
from app.tg_service.schemas import ForceReplySchema, TGCallbackQuerySchema

from .base import CallbackHandler, CommandHandler, MessageHandler


class _EntryAddMixin:
    """Entry add common methods."""

    @staticmethod
    def get_selected_budget_item(
            callback: TGCallbackQuerySchema, category: Category) -> BudgetItem:
        """Get selected budget item."""
        budget_item_id = int(callback.data)
        if not (budget_item := [b for b in category.budget_items if b.id == budget_item_id]):
            raise exceptoions.AccountantError(
                f'no budget item[{budget_item_id}] in category[{category.name}]')
        return budget_item[0]

    @staticmethod
    def get_state_budget_item(
            state: Optional[TGUserState], category: Category) -> tuple[Category, BudgetItem]:
        """Get state budget item."""
        budget_item: Optional[BudgetItem] = None
        error: Optional[str] = None
        if not (budget_item_id := state.data.budget_item_id):
            error = 'no state budget_item_id'
        elif not (budget_item := [b for b in category.budget_items if b.id == budget_item_id]):
            error = f'no budget_item[{budget_item_id}] in category[{category.name}]'
        if error:
            raise exceptoions.AccountantError(error)
        return budget_item[0]

    async def get_state_chat_budget_item(
            self, db: DatabaseAccessor, chat: TGChat,
            state: Optional[TGUserState]) -> ChatBudgetItem:
        """Get state chat budget item."""
        chat_budget_item: Optional[ChatBudgetItem] = None
        error: Optional[str] = None
        if not state:
            error = 'state not found'
        elif not (category_id := state.data.category_id):
            error = 'state category_id not found'
        elif not (budget_item_id := state.data.budget_item_id):
            error = 'state budget_item_id not found'
        elif not (chat_budget_item := await db.chat_budget_item_repo.get_chat_budget_item(
            chat_id=chat.id, category_id=category_id, budget_item_id=budget_item_id,
        )):
            error = 'state chat_budget_item not found'
        if error:
            raise exceptoions.AccountantError(error)
        return chat_budget_item

    @staticmethod
    async def make_message_entries_line(
            editor: TGMessageEditor, db: DatabaseAccessor, message_id: int) -> Optional[str]:
        """Get message entries line."""
        if not (data := await db.entry_repo.get_message_entries(message_id=message_id)):
            return None

        lines = []
        for category, budget_item, entry, valute in data:
            line = editor.make_entry_line(
                category_name=category.name,
                budget_item_name=budget_item.name,
                budget_item_type=budget_item.type,
                amount=entry.amount,
                valute_code=valute.code,
            )
            lines.append(line)
        return '\n'.join(lines)


class EntryAddHandler(CommandHandler):
    """Process click on /entry command."""

    async def handle(self) -> None:
        """Handle entry command."""
        chat = self.chat

        await self.delete_income_messages()
        keyboard = self.editor.get_category_keyboard(chat.categories)
        task = await self.send_message(ENTRY_ADD_CATEGORY, keyboard)
        await self.wait_task_result(
            task, CallbackHandlerEnum.ENTRY_ADD_CATEGORY, response_to_state={'message_id'})


class EntryAddCategoryHandler(CallbackHandler, _EntryAddMixin):
    """Process click on category."""

    async def handle(self) -> None:
        """Handle entry add category."""
        await super().handle()
        callback = self.update
        chat = self.chat

        message_id = callback.message.message_id
        category = self.get_selected_category()
        if not category.budget_items:
            text = ENTRY_ADD_NO_BUDGET_ITEMS_ERROR.format(category.name)
            keyboard = self.editor.get_category_keyboard(chat.categories)
            await self.edit_message(message_id, text, keyboard)
        else:
            keyboard = self.editor.get_budget_item_keyboard(category.budget_items)

            current_entry = self.editor.make_entry_line(category.name)
            text = '\n'.join([current_entry, ENTRY_ADD_BUDGET_ITEM])
            if entered := await self.make_message_entries_line(self.editor, self.db, message_id):
                text = '\n\n'.join([entered, text])

            task = await self.edit_message(message_id, text, keyboard)
            await self.wait_task_result(task, CallbackHandlerEnum.ENTRY_ADD_BUDGET_ITEM,
                                        state_data={'category_id': category.id})


class EntryAddBudgetItemHandler(CallbackHandler, _EntryAddMixin):
    """Process click on budget item."""

    async def handle(self) -> None:
        """Handle entry add budget item."""
        await super().handle()
        callback = self.update
        message_id = callback.message.message_id
        category = self.get_state_category()
        budget_item = self.get_selected_budget_item(callback, category)
        valutes = await self.get_chat_valutes()
        keyboard = self.editor.get_valute_keyboard(valutes)
        current_entry = self.editor.make_entry_line(
            category.name, budget_item.name, budget_item.type)
        text = '\n'.join([current_entry, ENTRY_ADD_VALUTE])
        if entered := await self.make_message_entries_line(self.editor, self.db, message_id):
            text = '\n\n'.join([entered, text])
        task = await self.edit_message(message_id, text, keyboard)
        await self.wait_task_result(task, CallbackHandlerEnum.ENTRY_ADD_VALUTE,
                                    state_data={'category_id': category.id,
                                                'budget_item_id': budget_item.id})


class EntryAddValuteHandler(CallbackHandler, _EntryAddMixin):
    """Process click on valute."""

    async def handle(self) -> None:
        """Handle entry add valute."""
        await super().handle()
        callback = self.update
        message_id = callback.message.message_id
        category = self.get_state_category()
        budget_item = self.get_state_budget_item(self.state, category)
        valute = self.get_selected_valute(chat=self.chat, callback=callback)
        text = self.editor.make_entry_line(
            category.name, budget_item.name, budget_item.type, valute_code=valute.code)
        if entered := await self.make_message_entries_line(self.editor, self.db, message_id):
            text = '\n\n'.join([entered, text])
        await self.edit_message(message_id, text)

        mention = self.editor.get_mention(self.user.username)
        text = ENTRY_ADD_AMOUNT.format(mention or '')
        keyboard = ForceReplySchema(input_field_placeholder=ENTRY_ADD_AMOUNT_PLACEHOLDER)
        task = await self.send_message(text, keyboard)
        await self.wait_task_result(task, MessageHandlerEnum.ENTRY_ADD_AMOUNT,
                                    state_data={'category_id': category.id,
                                                'budget_item_id': budget_item.id,
                                                'valute_id': valute.id,
                                                'message_id': message_id,
                                                'main_message_id': message_id},
                                    response_to_state={'message_id'})


class EntryAddAmountHandler(MessageHandler, _EntryAddMixin):
    """Process valute amount."""

    async def handle(self) -> None:
        """Handle valute amount."""
        await super().handle()
        await self.delete_income_messages(delete_reply_to_msg=True)
        amount: Optional[float] = None
        entered = self.update.text.strip()
        user = self.user
        chat = self.chat
        state = self.state
        try:
            amount = self._count_entered_amount(entered)
        except ValueError:
            pass
        if not amount:
            mention = self.editor.get_mention(user.username)
            text = ENTRY_ADD_AMOUNT_ERROR.format(entered)
            text += '\n' + ENTRY_ADD_AMOUNT.format(mention or '')
            keyboard = ForceReplySchema(input_field_placeholder=ENTRY_ADD_AMOUNT_PLACEHOLDER)
            task = await self.send_message(text, keyboard)
            await self.wait_task_result(task, MessageHandlerEnum.ENTRY_ADD_AMOUNT,
                                        state_data={**self.state.data_raw},
                                        response_to_state={'message_id'})
        else:
            chat_budget_item = await self.get_state_chat_budget_item(self.db, chat, state)
            valute = self.get_state_valute()
            entry_message_id = state.data.main_message_id

            entry = Entry(chat_budget_item_id=chat_budget_item.id,
                          valute_id=valute.id,
                          amount=amount,
                          data_raw={'message_id': entry_message_id})
            await self.db.entry_repo.create_item(entry)

            await self.set_state(
                CallbackHandlerEnum.ENTRY_ADD_FINISH, {'message_id': entry_message_id})
            keyboard = self.editor.get_finish_keyboard(chat.categories)
            text = ENTRY_ADD_ADDED
            if entered := await self.make_message_entries_line(
                    self.editor, self.db, entry_message_id):
                text = '\n\n'.join([entered, text])
            await self.edit_message(entry_message_id, text, keyboard)

    @staticmethod
    def _count_entered_amount(entered: str) -> float:
        """Count entered amount."""
        if '+' in entered:
            lines = entered.split('+')
        else:
            lines = [entered]

        lines = [line.strip() for line in lines]
        lines = [line for line in lines if line]
        lines = [float(line) for line in lines]

        return sum(lines)


class EntryAddFinishHandler(CallbackHandler, _EntryAddMixin):
    """Process click on finish."""

    async def handle(self) -> None:
        await super().handle()

        callback = self.update
        user = self.user
        state = self.state
        chat = self.chat

        message_id = callback.message.message_id
        decision = callback.data
        if decision == DecisionEnum.FINISH:
            text = ENTRY_ADD_FINISH
            details = str(message_id)
            if user.username:
                details = f'{user.username} {details}'
            text = '\n'.join([text, details])
            if entered := await self.make_message_entries_line(self.editor, self.db, message_id):
                text = '\n\n'.join([entered, text])
            await self.set_state(MessageHandlerEnum.DEFAULT, {})
            await self.edit_message(message_id, text)
        elif decision == DecisionEnum.MORE:
            await self.set_state(CallbackHandlerEnum.ENTRY_ADD_CATEGORY, {**state.data_raw})
            text = ENTRY_ADD_CATEGORY
            if entered := await self.make_message_entries_line(self.editor, self.db, message_id):
                text = '\n\n'.join([entered, text])
            keyboard = self.editor.get_category_keyboard(chat.categories)
            await self.edit_message(message_id, text, keyboard)
