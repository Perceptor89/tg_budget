import enum


class CommandHadlerEnum(str, enum.Enum):
    """Accountant command names."""

    CATEGORY_LIST = '/category_list'
    CATEGORY_ADD = '/category_add'
    CATEGORY_DELETE = '/category_delete'
    BUDGET_ITEM_ADD = '/budget_item_add'
    ENTRY_ADD = '/entry_add'
    REPORT = '/report'
    BALANCE_CREATE = '/balance_add'
    BALANCE_LIST = '/balance_list'
    BALANCE_SET = '/balance_set'
    BALANCE_DELETE = '/balance_delete'
    FOND_CREATE = '/fond_add'
    FOND_LIST = '/fond_list'
    FOND_SET = '/fond_set'
    FOND_DELETE = '/fond_delete'
    DEBT_CREATE = '/debt_add'
    DEBT_LIST = '/debt_list'
    DEBT_SET = '/debt_set'
    DEBT_DELETE = '/debt_delete'
    RATE_LIST = '/rate_list'


class MessageHandlerEnum(str, enum.Enum):
    """Accountant message names."""

    DEFAULT = 'default'
    CATEGORY_ADD_NAME = 'category_add_name'
    BUDGET_ITEM_ADD_NAME = 'budget_item_add_name'
    ENTRY_ADD_AMOUNT = 'entry_add_amount'
    BALANCE_CREATE_NAME = 'balance_add_name'
    BALANCE_SET_SAVE_AMOUNT = 'balance_set_save_amount'
    FOND_CREATE_NAME = 'fond_create_name'
    FOND_SET_SAVE_AMOUNT = 'fond_set_save_amount'
    DEBT_CREATE_NAME = 'debt_create_name'
    DEBT_SET_SAVE_AMOUNT = 'debt_set_save_amount'


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
    BALANCE_CREATE_VALUTE = 'balance_add_valute'
    BALANCE_SET_CHOOSE_ONE = 'balance_set_choose_one'
    BALANCE_DELETE_CHOOSE_ONE = 'balance_delete_choose_one'
    BALANCE_DELETE_CONFIRM = 'balance_delete_confirm'
    FOND_CREATE_VALUTE = 'fond_create_valute'
    FOND_SET_CHOOSE_ONE = 'fond_set_choose_one'
    FOND_DELETE_CHOOSE_ONE = 'fond_delete_choose_one'
    FOND_DELETE_CONFIRM = 'fond_delete_confirm'
    DEBT_CREATE_VALUTE = 'debt_create_valute'
    DEBT_SET_CHOOSE_ONE = 'debt_set_choose_one'
    DEBT_DELETE_CHOOSE_ONE = 'debt_delete_choose_one'
    DEBT_DELETE_CONFIRM = 'debt_delete_confirm'


class CommonCallbackHandlerEnum(str, enum.Enum):
    """Accountant common callback names."""
    HIDE = 'hide'


class DecisionEnum(str, enum.Enum):
    """User decisions names."""

    FINISH = 'finish'
    MORE = 'more'
