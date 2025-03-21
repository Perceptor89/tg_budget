import json
from typing import Optional

from app.accountant.enums import DecisionEnum
from app.constants import EMOJIES, MONTHS_MAPPER
from app.db_service.enums import BudgetItemTypeEnum
from app.db_service.models import BudgetItem, Category, Valute
from app.tg_service.schemas import InlineKeyboardButtonSchema, InlineKeyboardMarkup


KEYBOARD_ROWS_DEFAULT = 2


class TGMessageEditor:
    def create_inline_keyboard(
        self, buttons: list[tuple[str, str]], columns_amount: int = 1,
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
        if budget_items:
            buttons = [
                (
                    '{} {}'.format(b.name, self.get_emoji(b.type)),
                    str(b.id),
                )
                for b in budget_items]
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

    def make_entry_line(
        self,
        category_name: str,
        budget_item_name: Optional[str] = None,
        budget_item_type: Optional[str] = None,
        amount: Optional[float] = None,
        valute_code: Optional[str] = None,
    ) -> str:
        if not category_name:
            raise ValueError('category_name is empty')

        emoji = self.get_emoji(budget_item_type) if budget_item_type else None
        category_line = category_name.upper()
        line = category_line
        if budget_item_name:
            item_line = f'{budget_item_name} {emoji}' if emoji else budget_item_name
            line = f'{line} | {item_line}'
        if amount:
            amount_line = '{:.2f}'.format(amount)
            line = f'{line} {amount_line}'
        if valute_code:
            line = f'{line} {valute_code}'
        return line

    def make_category_list(self, categories: list[Category]) -> str:
        categories.sort(key=lambda c: c.name)
        lines = []
        for category in categories:
            category_line = '{}'.format(category.name.upper())
            lines.append(category_line)
            budget_items = category.budget_items
            budget_items.sort(key=lambda b: b.type)
            for budget_item in category.budget_items:
                emoji = self.get_emoji(budget_item.type)
                budget_item_line = '  {} {}'.format(budget_item.name, emoji)
                lines.append(budget_item_line)
        return '\n'.join(lines)

    def add_name_emoji(self, name: str) -> str:
        emoji = EMOJIES.get(name)
        if emoji:
            name = '{} {}'.format(name, emoji)
        return name

    def get_emoji(self, name: str) -> Optional[str]:
        return EMOJIES.get(name)

    def get_months_keyboard(self, months: list[int]) -> InlineKeyboardMarkup:
        buttons = [(MONTHS_MAPPER.get(m), str(m)) for m in months]
        return self.create_inline_keyboard(buttons, columns_amount=3)

    def get_years_keyboard(self, years: list[int]) -> InlineKeyboardMarkup:
        buttons = [(str(y), str(y)) for y in years]
        return self.create_inline_keyboard(buttons, columns_amount=1)

    def get_hide_keyboard(self, delete_also: Optional[list[int]] = None) -> InlineKeyboardMarkup:
        callback = dict(common_action='hide')
        if delete_also:
            callback['delete_also'] = delete_also
        button = ('Скрыть', json.dumps(callback))
        return self.create_inline_keyboard([button], columns_amount=1)
