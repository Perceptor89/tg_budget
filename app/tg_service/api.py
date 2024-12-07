from pydantic import BaseModel

from app.tg_service import schemas as api_schemas


class TGAPI:
    name: str
    request_shema: BaseModel
    response_schema: BaseModel


class SendMessage(TGAPI):
    name = 'sendMessage'
    request_schema = api_schemas.SendMessageRequestSchema
    response_schema = api_schemas.SendMessageResponseSchema


class DeleteMessage(TGAPI):
    name = 'deleteMessage'
    request_schema = api_schemas.DeleteMessageRequestSchema
    response_schema = None


class EditMessageText(TGAPI):
    name = 'editMessageText'
    request_shema = api_schemas.EditMessageTextRequestSchema
    response_schema = api_schemas.EditMessageTextResponseSchema


class EditMessageReplyMarkup(TGAPI):
    name = 'editMessageReplyMarkup'
    request_shema = api_schemas.EditMessageReplyMarkupRequestSchema
    response_schema = api_schemas.EditMessageReplyMarkupResponseSchema
