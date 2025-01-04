from app.db_service.enums import BudgetItemTypeEnum


MONTHS_MAPPER = {
    1: 'Январь',
    2: 'Февраль',
    3: 'Март',
    4: 'Апрель',
    5: 'Май',
    6: 'Июнь',
    7: 'Июль',
    8: 'Август',
    9: 'Сентябрь',
    10: 'Октябрь',
    11: 'Ноябрь',
    12: 'Декабрь',
}

EMOJIES = {
    BudgetItemTypeEnum.INCOME.value: '➕',
    BudgetItemTypeEnum.EXPENSE.value: '➖',
}
