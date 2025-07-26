from typing import Optional

from app.db_service.models import TGChat, TGUser, TGUserState
from app.tg_service import api
from app.tg_service import schemas as tg_schemas

from .. import messages
from ..enums import MessageHandlerEnum
from .base import CommandHandler, MessageHandler


class BalanceCreateHandler(CommandHandler):
    """Balance create handler."""

    async def handle(self, *, chat: TGChat, message: tg_schemas.TGMessageSchema, user: TGUser,
                     state: Optional[TGUserState], **_) -> None:
        """Process balance create command."""
        await self.call_tg(api.DeleteMessage, chat_id=chat.id, message_id=message.message_id)
        mention = self.editor.get_mention(user.username)
        text = messages.BALANCE_ADD_NAME.format(mention)
        keyboard = tg_schemas.ForceReplySchema(
            input_field_placeholder=messages.BALANCE_ADD_NAME_PLACEHOLDER)
        task = await self.call_tg(
            api.SendMessage, chat_id=chat.id, text=text, reply_murkup=keyboard)
        await task.event.wait()
        response: Optional[tg_schemas.SendMessageResponseSchema] = task.response
        if response:
            data_raw = dict(message_id=response.result.message_id)
            await self.set_state(user, state, MessageHandlerEnum.BALANCE_ADD_NAME, data_raw)


class BalanceAddNameHandler(MessageHandler):
    """Balance add name handler."""

    async def handle(self, *, chat: TGChat, message: tg_schemas.TGMessageSchema, user: TGUser,
                     state: Optional[TGUserState], **_) -> None:
        """Process balance add name message."""
        await super().handle(user=user, message=message, state=state, **_)
        for msg in [message, message.reply_to_message]:
            await self.call_tg(api.DeleteMessage, chat_id=chat.id, message_id=msg.message_id)
        

        
