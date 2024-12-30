from typing import Optional

from app.db_service.enums import BudgetItemTypeEnum
from app.db_service.models import ChatBudgetItem, TGChat, TGUser, TGUserState
from app.tg_service.schemas import (
    EditMessageTextResponseSchema,
    ForceReplySchema,
    SendMessageResponseSchema,
    TGCallbackQuerySchema,
    TGMessageSchema,
)

from ..enums import CallbackHandlerEnum, MessageHandlerEnum
from ..messages import (
    BUDGET_ITEM_ADD_CATEGORY,
    BUDGET_ITEM_ADD_EXISTS_ERROR,
    BUDGET_ITEM_ADD_LIMIT_ERROR,
    BUDGET_ITEM_ADD_NAME,
    BUDGET_ITEM_ADD_NAME_PLACEHOLDER,
    BUDGET_ITEM_ADD_TYPE,
    BUDGET_ITEM_ADDED,
)
from .base import BUDGET_ITEM_AMOUNT_LIMIT, CallbackHandler, CommandHandler, MessageHandler, logger


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
            text = BUDGET_ITEM_ADDED.format(category=category.name, budget_item=new_name, type=type.value)
            await self.delete_message(message.reply_to_message)
            await self.delete_message(message)
            await self.send_message(chat, message, text)
            await self.set_state(user, state, MessageHandlerEnum.DEFAULT, {})
