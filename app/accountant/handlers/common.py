from .base import CallbackHandler

from ..enums import CommonCallbackHandlerEnum
from ..registry import handler


@handler(CommonCallbackHandlerEnum.HIDE)
class HideCallbackHandler(CallbackHandler):
    """Hide callback handler."""

    async def handle(self) -> None:
        """Handle hide callback."""
        callback = self.update

        data = callback.data
        to_delete = [callback.message.message_id]
        if isinstance(data, dict) and (delete_also := data.get('delete_also')):
            to_delete.extend(delete_also)
        for msg_id in to_delete:
            await self.delete_message(msg_id)
