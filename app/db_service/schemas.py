from typing import Optional
from pydantic import BaseModel, Field

from app.db_service.enums import BudgetItemTypeEnum


class StateDataSchema(BaseModel):
    message_id: Optional[int] = Field(None)
    category_id: Optional[int] = Field(None)
    budget_item_type: Optional[BudgetItemTypeEnum] = Field(None)
    budget_item_id: Optional[int] = Field(None)
    valute_id: Optional[int] = Field(None)
    entries: list['StateEntryDataSchema'] = Field(default_factory=list)
    main_message_id: Optional[int] = Field(None)
    year: Optional[int] = Field(None)


class StateEntryDataSchema(BaseModel):
    category_name: str
    budget_item_name: str
    valute_code: str
    amount: float


class EntryDataSchema(BaseModel):
    message_id: int
