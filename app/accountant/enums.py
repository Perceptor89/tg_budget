import enum


class CommandHadlerEnum(str, enum.Enum):
    """Accountant command names."""

    CATEGORY_LIST = '/category_list'
    CATEGORY_ADD = '/category_add'
    CATEGORY_DELETE = '/category_delete'
    BUDGET_ITEM_ADD = '/budget_item_add'
    ENTRY_ADD = '/entry_add'
    REPORT = '/report'


class MessageHandlerEnum(str, enum.Enum):
    """Accountant message names."""

    CATEGORY_ADD_NAME = 'category_add_name'
    BUDGET_ITEM_ADD_NAME = 'budget_item_add_name'
    ENTRY_ADD_AMOUNT = 'entry_add_amount'
    DEFAULT = 'default'


class CallbackHandlerEnum(str, enum.Enum):
    """Accountant command names."""

    BUDGET_ITEM_ADD_CATEGORY = 'budget_item_add_category'
    BUDGET_ITEM_ADD_TYPE = 'budget_item_add_type'
    ENTRY_ADD_CATEGORY = 'entry_add_category'
    ENTRY_ADD_BUDGET_ITEM = 'entry_add_budget_item'
    ENTRY_ADD_VALUTE = 'entry_add_valute'
    ENTRY_ADD_FINISH = 'entry_add_finish'
    REPORT_SELECT_YEAR = 'report_select_year'
    REPORT_SELECT_MONTH = 'report_select_month'
    HIDE = 'hide'


class DecisionEnum(str, enum.Enum):
    """User decisions names."""

    FINISH = 'finish'
    MORE = 'more'
