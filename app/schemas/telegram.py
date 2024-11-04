from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, NaiveDatetime, field_validator


class TGChatSchema(BaseModel):
    id: int
    first_name: Optional[str] = Field(None)
    username: Optional[str] = Field(None)
    type: str
    title: Optional[str] = Field(None)
    all_members_are_administrators: Optional[bool] = Field(None)


class TGFromSchema(BaseModel):
    id: int
    is_bot: bool
    first_name: Optional[str] = Field(None)
    username: Optional[str] = Field(None)
    language_code: Optional[str] = Field(None)


class TGReplyToMessageSchema(BaseModel):
    message_id: int
    msg_from: TGFromSchema = Field(alias='from')
    chat: TGChatSchema
    date: NaiveDatetime
    edit_date: int
    text: str

    @field_validator('date', mode='before')
    def valid_timestamp(cls, v):
        date = datetime.fromtimestamp(v)
        return date


class TGMessageSchema(BaseModel):
    message_id: int
    msg_from: TGFromSchema = Field(alias='from')
    chat: TGChatSchema
    date: NaiveDatetime
    reply_to_message: Optional[TGReplyToMessageSchema] = Field(None)
    entities: Optional[list[dict]] = Field(None)
    text: str

    @field_validator('date', mode='before')
    def valid_timestamp(cls, v):
        date = datetime.fromtimestamp(v)
        return date


class TGUpdateSchema(BaseModel):
    update_id: int
    message: TGMessageSchema
