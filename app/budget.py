from enum import Enum
from app.db_service.repository import TGMessageRepo
from app.schemas.telegram import TGMessageSchema
from app.tg_service import TelegramClient
from app.db_service.models import TGMessage


class AccountantCommandEnum(str, Enum):
    """Accountant command names."""

    OUTCOME = '/command1'


class Accountant:
    tg_client: TelegramClient = None

    async def process_message(self, message: TGMessageSchema):
        if '#бюджет' in message.text:
            await self._save_message(message)

    async def _save_message(seelf, message: TGMessageSchema):
        repo: TGMessageRepo = TGMessageRepo()
        params = dict(
            message_id=message.message_id,
            date=message.date,
            chat_id=message.chat.id,
            other_info=message.model_dump(exclude={'message_id', 'date'}, exclude_none=True)
        )
        record = TGMessage(**params)
        await repo.create_item(record)
