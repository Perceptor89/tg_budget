SUCCESSFULLY_CREATED = 'Успешно создан'
SUCCESSFULLY_DELETED = 'Успешно удален'
AMOUNT_PLACEHOLDER = '123.45'
E_WRONG_AMOUNT_ENTERED = ('{mention}Неверный формат суммы `{entered_amount}`\n\n'
                          'Введи корректное значение')
VALUE_SAVED = 'Значение сохранено'
Q_SURE_DELETE = 'Точно хочешь удалить?'

NO_CATEGORIES = 'В чате пока нет ни одной категории'
CATEGORY_LIMIT_ERROR = 'Чат уже содержит максимальное количество категорий - {}'
CATEGORY_ENTER_NEW = '{}Введите название категории'
CATEGORY_ENTER_NEW_PLACEHOLDER = 'название категории'
CATEGORY_EXISTS_ERROR = 'Категория {} уже существует'
CATEGORY_CREATED = 'Категория `{}` создана'

BUDGET_ITEM_ADD_CATEGORY = 'Укажите категорию'
BUDGET_ITEM_ADD_NAME = 'Категория `{}`\nтип `{}`\n\n{}Введите название статьи'
BUDGET_ITEM_ADD_LIMIT_ERROR = 'Категория {} уже содержит максимальное количество статей - {}'
BUDGET_ITEM_ADD_NAME_PLACEHOLDER = 'название статьи'
BUDGET_ITEM_ADD_EXISTS_ERROR = ('Категория `{}`\n'
                                'статья `{}`\n'
                                'тип `{}`\n'
                                'Уже существует. {}Выбери другое название')
BUDGET_ITEM_ADD_TYPE = 'Выберите тип статьи'
BUDGET_ITEM_ADDED = ('категория `{category}`\ncтатья `{budget_item}`\nтип `{type}`\n\n'
                     'Успешно добавлена')

ENTRY_ADD_CATEGORY = 'Укажите категорию'
ENTRY_ADD_BUDGET_ITEM = 'Укажите статью'
ENTRY_ADD_NO_BUDGET_ITEMS_ERROR = (
    'В категории {} нет ни одной статьи\nВыберите другую или добавьте новую')
ENTRY_ADD_VALUTE = 'Выберите валюту'
ENTRY_ADD_AMOUNT = '{} Введите сумму'
ENTRY_ADD_AMOUNT_PLACEHOLDER = AMOUNT_PLACEHOLDER
ENTRY_ADD_AMOUNT_ERROR = 'Неверный формат суммы {}'
ENTRY_ADD_ADDED = 'Запись добавлена'
ENTRY_ADD_FINISH = 'Ввод завершен'

REPORT_SELECT_YEAR = 'ОТЧЕТ\nВыберите год'
REPORT_SELECT_MONTH = 'ОТЧЕТ\nгод {year}\nВыберите месяц'
REPORT_RESULT = 'ОТЧЕТ\nгод `{year}`\nмесяц `{month}`'
REPORT_NO_ENTRIES = 'В чате еще нет ни одной записи'

BALANCE_INFO = 'БАЛАНС\n`{balance_info}`'
BALANCE_CREATE_NAME = '{}Введите название баланса'
BALANCE_CREATE_NAME_PLACEHOLDER = 'Наличные USD'
BALANCE_CREATE_EXISTS_ERROR = ('Баланс `{}` уже существует\n\n'
                               '{}Введите другое название')
BALANCE_CREATE_VALUTE = 'Выберите валюту баланса'
BALANCE_CREATED = SUCCESSFULLY_CREATED

BALANCE_LIST_NO_BALANCES = 'В чате пока нет ни одного баланса'
BALANCE_LIST = 'БАЛАНСЫ\n\n{}'
BALANCE_SET_CHOOSE_ONE = 'Выбери баланс из списка'
BALANCE_SET_ENTER_AMOUNT_MAIN = 'БАЛАНС\n\n`{balance_info}`'
BALANCE_SET_ENTER_AMOUNT_REPLY = '{mention}Введите сумму'
BALANCE_SET_ENTER_AMOUNT_PLACEHOLDER = AMOUNT_PLACEHOLDER
BALANCE_SET_ENTER_AMOUNT_ERROR = E_WRONG_AMOUNT_ENTERED
BALANCE_SET_SAVED = VALUE_SAVED

BALANCE_DELETE_CHOOSE_ONE = 'Выбери баланс для удаления'
BALANCE_DELETE_APPROVE = Q_SURE_DELETE
BALANCE_DELETED = SUCCESSFULLY_DELETED

REPORT_ERROR = 'Не удалось сформировать отчет'

FOND_INFO = 'ФОНД\n`{fond_info}`'
FOND_CREATE_NAME = '{}Введите название фонда'
FOND_CREATE_NAME_PLACEHOLDER = 'Наличные USD'
FOND_CREATE_EXISTS_ERROR = 'Фонд `{}` уже существует\n\n{}Введите другое название'
FOND_CREATE_VALUTE = 'Выберите валюту фонда'
FOND_CREATED = SUCCESSFULLY_CREATED
FOND_LIST_NO_FONDS = 'В чате пока нет ни одного фонда'
FOND_LIST = 'ФОНДЫ\n\n{}'
FOND_SET_CHOOSE_ONE = 'Выбери фонд из списка'
FOND_SET_ENTER_AMOUNT_MAIN = 'ФОНД\n\n`{fond_name}`'
FOND_SET_ENTER_AMOUNT_REPLY = '{mention}Введите сумму'
FOND_SET_ENTER_AMOUNT_PLACEHOLDER = AMOUNT_PLACEHOLDER
FOND_SET_ENTER_AMOUNT_ERROR = E_WRONG_AMOUNT_ENTERED
FOND_SET_SAVED = VALUE_SAVED
FOND_DELETE_CHOOSE_ONE = 'Выбери фонд для удаления'
FOND_DELETE_APPROVE = Q_SURE_DELETE
FOND_DELETED = SUCCESSFULLY_DELETED

DEBT_INFO = 'ДОЛГ\n`{debt_info}`'
DEBT_CREATE_NAME = '{}Введите название долга'
DEBT_CREATE_NAME_PLACEHOLDER = 'Наличные USD'
DEBT_CREATE_EXISTS_ERROR = 'Долг `{}` уже существует\n\n{}Введите другое название'
DEBT_CREATE_VALUTE = 'Выберите валюту долга'
DEBT_CREATED = SUCCESSFULLY_CREATED
DEBT_LIST_NO_DEBTS = 'В чате пока нет ни одного долга'
DEBT_LIST = 'ДОЛГИ\n\n{}'
DEBT_SET_CHOOSE_ONE = 'Выбери долг из списка'
DEBT_SET_ENTER_AMOUNT_MAIN = 'ДОЛГ\n\n`{debt_name}`'
DEBT_SET_ENTER_AMOUNT_REPLY = '{mention}Введите сумму'
DEBT_SET_ENTER_AMOUNT_PLACEHOLDER = AMOUNT_PLACEHOLDER
DEBT_SET_ENTER_AMOUNT_ERROR = E_WRONG_AMOUNT_ENTERED
DEBT_SET_SAVED = VALUE_SAVED
DEBT_DELETE_CHOOSE_ONE = 'Выбери долг для удаления'
DEBT_DELETE_APPROVE = Q_SURE_DELETE
DEBT_DELETED = SUCCESSFULLY_DELETED

RATE_LIST_TITLE = 'КУРС ДОЛЛАРА\n'
