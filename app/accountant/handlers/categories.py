from typing import Optional

from app.db_service.models import Category, TGChat, TGUser, TGUserState
from app.tg_service import schemas as tg_schemas

from ..enums import MessageHandlerEnum
from ..messages import (
    CATEGORY_CREATED,
    CATEGORY_ENTER_NEW,
    CATEGORY_ENTER_NEW_PLACEHOLDER,
    CATEGORY_EXISTS_ERROR,
    CATEGORY_LIMIT_ERROR,
    NO_CATEGORIES,
)
from .base import CATEGORY_AMOUNT_LIMIT, CommandHandler, MessageHandler


class CategoryListHandler(CommandHandler):
    async def handle(
        self,
        *,
        chat: TGChat,
        message: tg_schemas.TGMessageSchema,
        **_,
    ) -> None:
        await self.delete_message(message)
        text: Optional[str] = None
        if chat.categories:
            text = self.editor.make_category_list(chat.categories)
        else:
            text = text or NO_CATEGORIES
        keyboard = self.editor.get_hide_keyboard()
        await self.send_message(chat, None, text, keyboard, is_answer=False)


class CategoryAddHandler(CommandHandler):
    async def handle(
        self,
        *,
        chat: TGChat,
        message: tg_schemas.TGMessageSchema,
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
            keyboard = tg_schemas.ForceReplySchema(
                input_field_placeholder=CATEGORY_ENTER_NEW_PLACEHOLDER,
            )
        task = await self.send_message(chat, message, text, keyboard, False)
        await task.event.wait()
        response: Optional[tg_schemas.SendMessageResponseSchema] = task.response
        if response:
            data_raw = dict(message_id=response.result.message_id)
            await self.set_state(user, state, MessageHandlerEnum.CATEGORY_ADD_NAME, data_raw)


class CategoryAddNameHandler(MessageHandler):
    async def handle(
        self,
        *,
        chat: TGChat,
        message: tg_schemas.TGMessageSchema,
        user: TGUser,
        state: Optional[TGUserState],
        **_,
    ) -> None:
        await self.delete_message(message)
        await self.delete_message(message.reply_to_message)
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
        await self.send_message(chat, message, text, is_answer=False)
        await self.set_state(user, state, MessageHandlerEnum.DEFAULT, {})
