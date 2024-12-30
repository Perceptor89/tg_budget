from .base import CallbackHandler
from app.tg_service.schemas import TGCallbackQuerySchema


class HideCallbackHandler(CallbackHandler):
    async def handle(
        self,
        *,
        callback: TGCallbackQuerySchema,
        **_,
    ) -> None:
        await self.delete_message(callback.message)
