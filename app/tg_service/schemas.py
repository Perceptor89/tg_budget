import datetime
from functools import cached_property
from typing import Optional, Union

from pydantic import BaseModel, Field

from .enums import TGChatTypeEnum, TGEntityTypeEnum


class TGChatSchema(BaseModel):
    tg_id: int = Field(alias='id')
    first_name: Optional[str] = Field(None)
    username: Optional[str] = Field(None)
    type: TGChatTypeEnum
    title: Optional[str] = Field(None)
    all_members_are_administrators: Optional[bool] = Field(None)


class TGFromSchema(BaseModel):
    tg_id: int = Field(alias='id')
    is_bot: bool
    first_name: Optional[str] = Field(None)
    username: Optional[str] = Field(None)
    language_code: Optional[str] = Field(None)


class TGReplyToMessageSchema(BaseModel):
    message_id: int
    msg_from: TGFromSchema = Field(alias='from')
    chat: TGChatSchema  
    date: datetime.datetime
    edit_date: Optional[datetime.datetime] = Field(None)
    text: str


class TGEntitySchema(BaseModel):

    offset: int
    length: int
    type: TGEntityTypeEnum


class TGMessageSchema(BaseModel):
    message_id: int
    msg_from: TGFromSchema = Field(alias='from')
    chat: TGChatSchema
    date: datetime.datetime
    reply_to_message: Optional[TGReplyToMessageSchema] = Field(None)
    entities: list[TGEntitySchema] = Field(default_factory=list)
    text: str

    @cached_property
    def command(self) -> Optional[str]:
        command = [e for e in self.entities if e.type == TGEntityTypeEnum.BOT_COMMAND]
        if command:
            command = command[0]
            return self.text[command.offset:command.length].split('@')[0]


class TGUpdateSchema(BaseModel):
    update_id: int
    message: TGMessageSchema


class RequestSchema(BaseModel):
    ...


class ResponseSchema(BaseModel):
    ...


class SendMessageRequestSchema(RequestSchema):
    chat_id: Union[int, str]
    text: str
    reply_parameters: Optional['ReplyParametersRequestSchema'] = Field(None)
    reply_markup: Union[None, 'ForceReplySchema'] = Field(None)


class ReplyParametersRequestSchema(RequestSchema):
    message_id: int
    chat_id: Union[int, str]
    allow_sending_without_reply: bool = Field(True)


class ForceReplySchema(RequestSchema):
    force_reply: bool = Field(True)
    input_field_placeholder: Optional[str] = Field(None)
    selective: Optional[bool] = Field(True)
