from app.db_service.enums import BudgetItemTypeEnum
from app.db_service.models import BudgetItem, ChatBudgetItem
from app.tg_service.btn_labels import BUTTON_LABELS
from app.tg_service.schemas import ForceReplySchema

from .. import constants
from ..enums import CallbackHandlerEnum, CommandHadlerEnum, MessageHandlerEnum
from ..messages import (
    BUDGET_ITEM_ADD_CATEGORY,
    BUDGET_ITEM_ADD_EXISTS_ERROR,
    BUDGET_ITEM_ADD_LIMIT_ERROR,
    BUDGET_ITEM_ADD_NAME,
    BUDGET_ITEM_ADD_NAME_PLACEHOLDER,
    BUDGET_ITEM_ADD_TYPE,
    BUDGET_ITEM_ADDED,
)
from ..registry import handler
from .base import CallbackHandler, CommandHandler, MessageHandler


@handler(CommandHadlerEnum.BUDGET_ITEM_ADD)
class BudgetItemAddHandler(CommandHandler):
    """Process click on /budget_item_add command."""

    async def handle(self) -> None:
        """Handle budget_item_add command."""
        chat = self.chat
        await self.delete_income_messages()
        keyboard = self.editor.get_category_keyboard(chat.categories)
        task = await self.send_message(BUDGET_ITEM_ADD_CATEGORY, keyboard)
        await self.wait_task_result(task, CallbackHandlerEnum.BUDGET_ITEM_ADD_CATEGORY,
                                    response_to_state={'message_id'})


@handler(CallbackHandlerEnum.BUDGET_ITEM_ADD_CATEGORY)
class BudgetItemAddCategoryHandler(CallbackHandler):
    """Process budget item add category."""

    async def handle(self) -> None:
        """Handler budget item category."""
        chat = self.chat
        message_id = self.update.message.message_id
        await super().handle()
        category = self.get_selected_category()
        if len(category.budget_items) >= constants.BUDGET_ITEM_AMOUNT_LIMIT:
            text = BUDGET_ITEM_ADD_LIMIT_ERROR.format(
                category.name, constants.BUDGET_ITEM_AMOUNT_LIMIT)
            keyboard = self.editor.get_category_keyboard(chat.categories)
            await self.edit_message(message_id, text, keyboard)
        else:
            text = BUDGET_ITEM_ADD_TYPE
            keyboard = self.editor.get_budget_item_type_keyboard()
            task = await self.edit_message(message_id, text, keyboard)
            await self.wait_task_result(task, CallbackHandlerEnum.BUDGET_ITEM_ADD_TYPE,
                                        state_data={'message_id': message_id,
                                                    'category_id': category.id})


@handler(CallbackHandlerEnum.BUDGET_ITEM_ADD_TYPE)
class BudgetItemAddTypeHandler(CallbackHandler):
    """Process budget item add type."""

    async def handle(self) -> None:
        """Handle budget item type."""
        await super().handle()
        await self.delete_income_messages()
        callback = self.update
        type_ = BudgetItemTypeEnum(callback.data)
        category = self.get_state_category()
        mention = self.editor.get_mention(self.user.username)
        text = BUDGET_ITEM_ADD_NAME.format(
            category.name, BUTTON_LABELS[type_.value.lower()], f'{mention} ' if mention else '')
        keyboard = ForceReplySchema(input_field_placeholder=BUDGET_ITEM_ADD_NAME_PLACEHOLDER)
        task = await self.send_message(text, keyboard)
        await self.wait_task_result(task, MessageHandlerEnum.BUDGET_ITEM_ADD_NAME,
                                    state_data={'category_id': category.id,
                                                'budget_item_type': type_.value},
                                    response_to_state={'message_id'})


@handler(MessageHandlerEnum.BUDGET_ITEM_ADD_NAME)
class BudgetItemAddNameHandler(MessageHandler):
    """Process budget item add name."""

    async def handle(self) -> None:
        """Handle budget item name."""
        await super().handle()
        await self.delete_income_messages(delete_reply_to_msg=True)
        state = self.state
        message = self.update
        chat = self.chat
        user = self.user
        category = self.get_state_category()
        new_name = message.text.strip()
        repo = self.db.chat_budget_item_repo
        type_ = BudgetItemTypeEnum(state.data.budget_item_type)
        if await repo.get_chat_budget_item(
            chat_id=chat.id,
            category_id=category.id,
            budget_item_name=new_name,
            budget_item_type=type_,
        ):
            mention = self.editor.get_mention(user.username)
            text = BUDGET_ITEM_ADD_EXISTS_ERROR.format(
                category.name, new_name, type_.value, f'{mention} ' if mention else '')
            keyboard = ForceReplySchema(input_field_placeholder=BUDGET_ITEM_ADD_NAME_PLACEHOLDER)
            task = await self.send_message(text, keyboard)
            await self.wait_task_result(task, MessageHandlerEnum.BUDGET_ITEM_ADD_NAME,
                                        state_data={**state.data_raw},
                                        response_to_state={'message_id'})
        else:
            budget_item = await self.get_or_create_budget_item(new_name, type_)
            if (chat_budget_item := await repo.get_no_budget_item_row(
                    chat_id=chat.id, category_id=category.id)):
                chat_budget_item.budget_item_id = budget_item.id
                await repo.update_item(chat_budget_item)
            else:
                chat_budget_item = ChatBudgetItem(chat_id=chat.id,
                                                  category_id=category.id,
                                                  budget_item_id=budget_item.id)
                await repo.create_item(chat_budget_item)
            text = BUDGET_ITEM_ADDED.format(
                category=category.name.upper(), budget_item=new_name,
                type=BUTTON_LABELS[type_.value.lower()])
            keyboard = self.editor.get_hide_keyboard()
            await self.send_message(text, keyboard)
            await self.set_state(MessageHandlerEnum.DEFAULT, {})

    async def get_or_create_budget_item(self, name: str, type_: BudgetItemTypeEnum) -> BudgetItem:
        """Get or create budget item."""
        if not (budget_item := await self.db.budget_item_repo.get_by_name_type(
                name=name, type=type_)):
            budget_item = BudgetItem(name=name, type=type_.value)
            budget_item = await self.db.budget_item_repo.create_item(budget_item)
        return budget_item
