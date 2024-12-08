from typing import Optional
from app.accountant.enums import DecisionEnum
from app.db_service.enums import BudgetItemTypeEnum
from app.db_service.models import BudgetItem, Category, Valute
from app.db_service.schemas import StateEntryDataSchema
from app.tg_service.schemas import InlineKeyboardButtonSchema, InlineKeyboardMarkup


KEYBOARD_ROWS_DEFAULT = 3


class TGMessageEditor:
    def create_inline_keyboard(
        self, buttons: list[tuple[str, str]], columns_amount: int,
    ) -> InlineKeyboardMarkup:
        buttons = [
            InlineKeyboardButtonSchema(text=text, callback_data=callback_data)
            for text, callback_data in buttons
        ]
        return InlineKeyboardMarkup(
            inline_keyboard=list(self.split_into_chunks(buttons, columns_amount)),
        )

    @staticmethod
    def split_into_chunks(items: list, chunk_size: int):
        for i in range(0, len(items), chunk_size):
            yield items[i:i + chunk_size]

    @staticmethod
    def get_mention(user: str) -> Optional[str]:
        return f'@{user}' if user else None

    def get_category_keyboard(self, categories: list[Category]) -> InlineKeyboardMarkup:
        buttons = [(c.name, c.name) for c in categories]
        return self.create_inline_keyboard(buttons, KEYBOARD_ROWS_DEFAULT)

    def get_budget_item_type_keyboard(self) -> InlineKeyboardMarkup:
        buttons = [(t.value, t.value) for t in BudgetItemTypeEnum]
        return self.create_inline_keyboard(buttons, KEYBOARD_ROWS_DEFAULT)

    def get_budget_item_keyboard(self, budget_items: list[BudgetItem]) -> InlineKeyboardMarkup:
        emoji = {
            BudgetItemTypeEnum.INCOME: '➕',
            BudgetItemTypeEnum.EXPENSE: '➖',
        }
        if budget_items:
            buttons = [(b.name + ' ' + emoji[b.type], b.name) for b in budget_items]
            return self.create_inline_keyboard(buttons, KEYBOARD_ROWS_DEFAULT)

    def get_valute_keyboard(self, valutes: list[Valute]) -> InlineKeyboardMarkup:
        buttons = [(v.code, v.code) for v in valutes]
        return self.create_inline_keyboard(buttons, KEYBOARD_ROWS_DEFAULT)

    def get_finish_keyboard(self, is_more: bool = True) -> InlineKeyboardMarkup:
        ru_names = {
            DecisionEnum.FINISH: 'Завершить',
            DecisionEnum.MORE: 'Еще',
        }
        buttons_names = [DecisionEnum.FINISH]
        if is_more:
            buttons_names.append(DecisionEnum.MORE)
        buttons = [(ru_names.get(name), name.value) for name in buttons_names]
        return self.create_inline_keyboard(buttons, KEYBOARD_ROWS_DEFAULT)

    def add_state_entries_lines(self, text: str, entries: list[StateEntryDataSchema]) -> str:
        if not entries:
            return text
        lines = []
        for entry in entries:
            line = f'{entry.category_name} - {entry.budget_item_name} - {entry.valute_code} - {entry.amount}'
            lines.append(line)
        return '\n'.join(lines) + '\n\n' + text
