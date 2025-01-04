from typing import Optional

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
from app.db_service.models import Entry, TGChat, TGUser, TGUserState
from app.tg_service.schemas import (
    EditMessageTextResponseSchema,
    ForceReplySchema,
    SendMessageResponseSchema,
    TGCallbackQuerySchema,
    TGMessageSchema,
)

from .base import CallbackHandler, CommandHandler, MessageHandler


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
        await super().handle(callback=callback, state=state, **_)
        message_id = callback.message.message_id

        if not (category := self.get_selected_category(chat, callback)):
            return
        if not category.budget_items:
            text = ENTRY_ADD_NO_BUDGET_ITEMS_ERROR.format(category.name)
            keyboard = self.editor.get_category_keyboard(chat.categories)
            await self.edit_message(chat.tg_id, message_id, text, keyboard)
        else:
            keyboard = self.editor.get_budget_item_keyboard(category.budget_items)

            current_entry = self.editor.make_entry_line(category.name)
            text = '\n'.join([current_entry, ENTRY_ADD_BUDGET_ITEM])
            if entered := await self.get_message_entries_line(message_id=message_id):
                text = '\n\n'.join([entered, text])

            task = await self.edit_message(chat.tg_id, message_id, text, keyboard)
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
        message_id = callback.message.message_id
        category = self.get_state_category(chat=chat, state=state)
        budget_item = self.get_selected_budget_item(chat=chat, state=state, callback=callback)
        valutes = await self.get_chat_valutes(chat=chat)
        keyboard = self.editor.get_valute_keyboard(valutes)
        current_entry = self.editor.make_entry_line(category.name, budget_item.name, budget_item.type)
        text = '\n'.join([current_entry, ENTRY_ADD_VALUTE])
        if entered := await self.get_message_entries_line(message_id=message_id):
            text = '\n\n'.join([entered, text])
        task = await self.edit_message(chat.tg_id, message_id, text, keyboard)
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
        message_id = callback.message.message_id
        category, budget_item = self.get_state_budget_item(chat=chat, state=state)
        valute = self.get_selected_valute(chat=chat, callback=callback)

        text = self.editor.make_entry_line(category.name, budget_item.name, budget_item.type, valute_code=valute.code)
        if entered := await self.get_message_entries_line(message_id=message_id):
            text = '\n\n'.join([entered, text])
        await self.edit_message(chat.tg_id, message_id, text)

        mention = self.editor.get_mention(user.username)
        text = ENTRY_ADD_AMOUNT.format(mention or '')
        keyboard = ForceReplySchema(input_field_placeholder=ENTRY_ADD_AMOUNT_PLACEHOLDER)
        task = await self.send_message(chat, None, text, keyboard, is_answer=False)
        await task.event.wait()
        response: Optional[SendMessageResponseSchema] = task.response
        if response:
            data_raw = state.data_raw
            data_raw['valute_id'] = valute.id
            data_raw['message_id'] = response.result.message_id
            data_raw['main_message_id'] = message_id
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
            amount = _count_entry_amount(inputed)
        except ValueError:
            pass
        if not amount:
            mention = self.editor.get_mention(user.username)
            text = ENTRY_ADD_AMOUNT_ERROR.format(inputed)
            text += '\n' + ENTRY_ADD_AMOUNT.format(mention or '')
            keyboard = ForceReplySchema(input_field_placeholder=ENTRY_ADD_AMOUNT_PLACEHOLDER)
            task = await self.send_message(chat, None, text, keyboard, is_answer=False)
            await task.event.wait()
            response: Optional[SendMessageResponseSchema] = task.response
            if response:
                data_raw = state.data_raw
                data_raw['message_id'] = response.result.message_id
                await self.set_state(user, state, MessageHandlerEnum.ENTRY_ADD_AMOUNT, data_raw)
        else:
            chat_budget_item = await self.get_state_chat_budget_item(chat=chat, state=state)
            valute = self.get_state_valute(chat=chat, state=state)
            entry_message_id = state.data.main_message_id

            entry = Entry(
                chat_budget_item_id=chat_budget_item.id,
                valute_id=valute.id,
                amount=amount,
                data_raw=dict(message_id=entry_message_id),
            )
            await self.db.entry_repo.create_item(entry)

            data_raw = dict(message_id=entry_message_id)
            await self.set_state(user, state, CallbackHandlerEnum.ENTRY_ADD_FINISH, data_raw)
            keyboard = self.editor.get_finish_keyboard(chat.categories)
            text = ENTRY_ADD_ADDED
            if entered := await self.get_message_entries_line(message_id=entry_message_id):
                text = '\n\n'.join([entered, text])
            await self.edit_message(chat.tg_id, entry_message_id, text, keyboard)


def _count_entry_amount(inputed: str) -> float:
    if '+' in inputed:
        lines = inputed.split('+')
    else:
        lines = [inputed]

    lines = [line.strip() for line in lines]
    lines = [line for line in lines if line]
    lines = [float(line) for line in lines]

    return sum(lines)


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
        message_id = callback.message.message_id
        decision = callback.data
        if decision == DecisionEnum.FINISH:
            text = ENTRY_ADD_FINISH
            details = str(message_id)
            if user.username:
                details = '{} {}'.format(user.username, details)
            text = '\n'.join([text, details])
            if entered := await self.get_message_entries_line(message_id=message_id):
                text = '\n\n'.join([entered, text])
            await self.set_state(user, state, MessageHandlerEnum.DEFAULT, {})
            await self.edit_message(chat.tg_id, message_id, text)
        elif decision == DecisionEnum.MORE:
            await self.set_state(user, state, CallbackHandlerEnum.ENTRY_ADD_CATEGORY, state.data_raw)
            text = ENTRY_ADD_CATEGORY
            if entered := await self.get_message_entries_line(message_id=message_id):
                text = '\n\n'.join([entered, text])
            keyboard = self.editor.get_category_keyboard(chat.categories)
            await self.edit_message(chat.tg_id, message_id, text, keyboard)
