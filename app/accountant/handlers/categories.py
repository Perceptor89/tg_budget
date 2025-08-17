from app.db_service.models import Category
from app.tg_service import schemas as tg_schemas

from .. import constants
from ..enums import MessageHandlerEnum
from ..messages import (
    CATEGORY_CREATED,
    CATEGORY_ENTER_NEW,
    CATEGORY_ENTER_NEW_PLACEHOLDER,
    CATEGORY_EXISTS_ERROR,
    CATEGORY_LIMIT_ERROR,
    NO_CATEGORIES,
)
from .base import CommandHandler, MessageHandler


class CategoryListHandler(CommandHandler):
    """Process click on /category_list command."""

    async def handle(self) -> None:
        """Handle category list command."""
        await self.delete_income_messages()
        categories = self.chat.categories
        text = self.editor.make_category_list(categories) if categories else NO_CATEGORIES
        keyboard = self.editor.get_hide_keyboard()
        await self.send_message(text, keyboard)


class CategoryAddHandler(CommandHandler):
    """Process click on /category_add command."""

    async def handle(self) -> None:
        """Handle category add command."""
        await self.delete_income_messages()
        if len(self.chat.categories) >= constants.CATEGORY_AMOUNT_LIMIT:
            text = CATEGORY_LIMIT_ERROR.format(constants.CATEGORY_AMOUNT_LIMIT)
            keyboard = None
        else:
            mention = self.editor.get_mention(self.user.username)
            text = CATEGORY_ENTER_NEW.format(f'{mention} ' if mention else '')
            keyboard = tg_schemas.ForceReplySchema(
                input_field_placeholder=CATEGORY_ENTER_NEW_PLACEHOLDER,
            )
        task = await self.send_message(text, keyboard)
        await self.wait_task_result(task, MessageHandlerEnum.CATEGORY_ADD_NAME,
                                    response_to_state={'message_id'})


class CategoryAddNameHandler(MessageHandler):
    """Process category add name."""

    async def handle(self) -> None:
        """Handle category add name."""
        chat = self.chat

        await super().handle()
        await self.delete_income_messages(delete_reply_to_msg=True)
        categories = chat.categories
        new_name = self.update.text.strip()
        is_exists = bool([c.name for c in categories if c.name.lower() == new_name.lower()])
        if is_exists:
            text = CATEGORY_EXISTS_ERROR.format(new_name)
        else:
            if not (category := await self.db.category_repo.get_by_name(new_name)):
                category = Category(name=new_name)
            chat.categories.append(category)
            await self.db.chat_repo.update_item(chat)
            text = CATEGORY_CREATED.format(new_name)
        keyboard = self.editor.get_hide_keyboard()
        await self.send_message(text, keyboard)
        await self.set_state(MessageHandlerEnum.DEFAULT, {})
