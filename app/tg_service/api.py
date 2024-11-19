from pydantic import BaseModel

from app.tg_service import schemas as api_schemas


class TGAPI:
    name: str
    request_shema: BaseModel
    response_schema: BaseModel


class SendMessage(TGAPI):
    name = 'sendMessage'
    request_schema = api_schemas.SendMessageRequestSchema
    response_schema = None
