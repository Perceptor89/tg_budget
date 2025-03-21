from app.tg_service import api as tg_api
from app.tg_service.schemas import TGCallbackQuerySchema

from .base import CallbackHandler


class HideCallbackHandler(CallbackHandler):
    async def handle(
        self,
        *,
        callback: TGCallbackQuerySchema,
        **_,
    ) -> None:
        data = callback.data
        chat_id = callback.message.chat.tg_id
        to_delete = [callback.message.message_id]
        if isinstance(data, dict) and (delete_also := data.get('delete_also')):
            to_delete.extend(delete_also)
        for msg_id in to_delete:
            await self.call_tg(tg_api.DeleteMessage, chat_id=chat_id, message_id=msg_id)
