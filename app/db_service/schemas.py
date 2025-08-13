from typing import Optional
from pydantic import BaseModel, Field

from app.db_service.enums import BudgetItemTypeEnum


class StateDataSchema(BaseModel):
    """User state raw data."""

    message_id: Optional[int] = Field(None)
    category_id: Optional[int] = Field(None)
    budget_item_type: Optional[BudgetItemTypeEnum] = Field(None)
    budget_item_id: Optional[int] = Field(None)
    valute_id: Optional[int] = Field(None)
    main_message_id: Optional[int] = Field(None)
    year: Optional[int] = Field(None)
    balance_name: Optional[str] = Field(None)


class EntryDataSchema(BaseModel):
    """Entry raw data."""

    message_id: int
