import enum


class BudgetItemTypeEnum(str, enum.Enum):
    """Budget item type enum."""

    INCOME = 'INCOME'
    EXPENSE = 'EXPENSE'
