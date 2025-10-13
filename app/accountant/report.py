from collections import defaultdict
from dataclasses import dataclass
import datetime
from functools import cached_property
from io import BytesIO
from statistics import geometric_mean
from typing import Literal, Optional

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import seaborn as sns

from app.constants import USD_CODE, USDT_CODE
from app.db_service import DatabaseAccessor
from app.db_service.enums import BudgetItemTypeEnum
from app.db_service.models import BudgetItem, Category, ChatBalance, ChatDebt, ChatFond, Valute, ValuteExchange


class ReportError(Exception):
    """Report error."""


class NoRawDataError(ReportError):
    """No raw data error."""


class NoRatesError(ReportError):
    """No rates error."""


class NoValuteError(ReportError):
    """Report valute error."""


@dataclass
class ReportBudgetItem:
    """Report budget item."""

    name: str
    amount: float
    category_name: str
    type_: BudgetItemTypeEnum

    @property
    def amount_str(self):
        return f'{self.amount:.2f}'

    @property
    def label(self):
        return f'{self.category_name} | {self.name} - {self.amount_str}'


@dataclass
class ReportCategory:
    """Report category."""

    name: str
    budget_items: list[ReportBudgetItem]

    @property
    def income(self):
        return sum(bi.amount for bi in self.budget_items if bi.type_ == BudgetItemTypeEnum.INCOME)

    @property
    def expense(self):
        return sum(bi.amount for bi in self.budget_items if bi.type_ == BudgetItemTypeEnum.EXPENSE)

    @property
    def income_str(self):
        return f'{self.income:.2f}'

    @property
    def expense_str(self):
        return f'{self.expense:.2f}'


class _ReportBase:
    """Budget report base."""

    valute_code: str
    db: 'DatabaseAccessor'
    chat_id: int

    period0: Optional[datetime.date] = None
    period1: Optional[datetime.date] = None
    valute: Optional[Valute] = None
    rates: dict[str, dict[str, float]] = None  # {valute_code: {'avg': rate, 'cur': rate}}

    REPORT_IMAGE_WIDTH = 7
    REPORT_TEXT_FAMILY = 'monospace'

    def __init__(self, db: 'DatabaseAccessor', chat_id: int, valute_code: str) -> None:
        """Init report base."""
        self.db = db
        self.chat_id = chat_id
        self.valute_code = valute_code
        self.rates = {}

    RATE_PRECISION = 6
    VALUTE_SUBSTITUTES = {
        USD_CODE: [USDT_CODE],
        USDT_CODE: [USD_CODE],
    }

    async def _load_valute(self) -> None:
        """Load valute from database."""
        if not (valute := await self.db.valute_repo.get_by_code(self.valute_code)):
            raise NoValuteError(f'report valute {self.valute_code} not found')
        self.valute = valute

    async def _get_valute_rates(self, rates_to_find: set[Valute]) -> dict[str, dict[str, float]]:
        rates = defaultdict(lambda: {'avg': 0.0, 'cur': 0.0})
        usd = await self.db.valute_repo.get_by_code(USD_CODE)

        for valute in rates_to_find:
            direct = await self._get_exchange_rate(valute, self.valute)
            direct_cur = await self._get_exchange_rate(valute, self.valute, last_one=True)
            if direct:
                rates[valute.code]['avg'] = direct
                rates[valute.code]['cur'] = direct_cur
                continue
            valute_to_usd = await self._get_exchange_rate(valute, usd)
            usd_to_target = await self._get_exchange_rate(usd, valute)
            valute_to_usd_cur = await self._get_exchange_rate(valute, usd, last_one=True)
            usd_to_target_cur = await self._get_exchange_rate(usd, valute, last_one=True)
            if valute_to_usd and usd_to_target:
                rates[valute.code]['avg'] = round(
                    valute_to_usd * usd_to_target, self.RATE_PRECISION)
                rates[valute.code]['cur'] = round(
                    valute_to_usd_cur * usd_to_target_cur, self.RATE_PRECISION)
                continue
            valute_to_usd = await self._get_daily_rate(valute, usd)
            valute_to_usd_cur = await self._get_daily_rate(valute, usd, last_one=True)
            if self.valute.code in [USD_CODE, USDT_CODE]:
                usd_to_target = 1
                usd_to_target_cur = 1
            else:
                usd_to_target = await self._get_daily_rate(usd, valute)
                usd_to_target_cur = await self._get_daily_rate(usd, valute, last_one=True)
            if valute_to_usd and usd_to_target:
                rates[valute.code]['avg'] = round(
                    valute_to_usd * usd_to_target, self.RATE_PRECISION)
                rates[valute.code]['cur'] = round(
                    valute_to_usd_cur * usd_to_target_cur, self.RATE_PRECISION)
        return rates

    async def _get_exchange_rate(
            self, valute_from: Valute, valute_to: Valute,
            last_one: bool = False) -> Optional[float]:
        rates = []
        from_codes = [valute_from.code] + self.VALUTE_SUBSTITUTES.get(valute_from.code, [])
        to_codes = [valute_to.code] + self.VALUTE_SUBSTITUTES.get(valute_to.code, [])
        exchanges: list[ValuteExchange] = await self.db.valute_exchange_repo.get_pair_exchanges(
            from_codes, to_codes, self.period0, self.period1, last_one=last_one)
        for exchange in exchanges:
            rate = round(
                exchange.valute_to_amount / exchange.valute_from_amount, self.RATE_PRECISION)
            rates.append(rate)
        exchanges = await self.db.valute_exchange_repo.get_pair_exchanges(
            to_codes, from_codes, self.period0, self.period1, last_one=last_one)
        for exchange in exchanges:
            rate = round(
                exchange.valute_from_amount / exchange.valute_to_amount, self.RATE_PRECISION)
            rates.append(rate)
        return geometric_mean(rates) if rates else None

    async def _get_daily_rate(
            self, valute_from: Valute, valute_to: Valute,
            last_one: bool = False) -> Optional[float]:
        rates = []
        from_codes = [valute_from.code] + self.VALUTE_SUBSTITUTES.get(valute_from.code, [])
        to_codes = [valute_to.code] + self.VALUTE_SUBSTITUTES.get(valute_to.code, [])
        daily_rates = await self.db.valute_rate_repo.get_period_rates(
            from_codes, to_codes, self.period0, self.period1, last_one=last_one)
        for rate in daily_rates:
            rates.append(rate.rate)
        daily_rates = await self.db.valute_rate_repo.get_period_rates(
            to_codes, from_codes, self.period0, self.period1, last_one=last_one)
        for rate in daily_rates:
            rate = round(1 / rate.rate, self.RATE_PRECISION)
            rates.append(rate)
        return geometric_mean(rates) if rates else None

    async def _load_rates(self, used_valutes: set[Valute]) -> None:
        """Load rates."""
        substitutes = self.VALUTE_SUBSTITUTES.get(self.valute.code, [])
        rates_to_find = set(v for v
                            in used_valutes
                            if (v.code != self.valute.code) and v.code not in substitutes)

        rates = await self._get_valute_rates(rates_to_find)
        to_find = {v.code for v in rates_to_find}
        found = set(rates.keys())
        if found != to_find:
            raise NoRatesError(f'rates not found {to_find - found}')
        default_rate = {'avg': 1, 'cur': 1}
        if substitutes:
            rates.update(dict.fromkeys(substitutes, default_rate))
        rates.update({self.valute.code: default_rate})
        self.rates = rates


class Report(_ReportBase):
    """Budget Report."""

    period0: datetime.date
    period1: datetime.date

    raw_data: list[tuple[Category, BudgetItem, Valute, int]] = None
    categories: list[ReportCategory] = None
    image: Optional[bytes] = None

    PIE_CHART_HEIGHT = 5
    LEGEND_ITEM_HEIGHT = 0.2

    def __init__(self, valute_code: str, chat_id: int, period0: datetime.date,
                 period1: datetime.date, db: 'DatabaseAccessor') -> None:
        super().__init__(db=db, chat_id=chat_id, valute_code=valute_code)
        self.period0 = period0
        self.period1 = period1
        self.rates = {}
        self.raw_data = []
        self.categories = []

    @cached_property
    def income(self) -> float:
        """Income sum."""
        return sum(c.income for c in self.categories)

    @cached_property
    def income_items_count(self) -> int:
        """Count of income items in all categories."""
        return sum(len([item for item in category.budget_items
                       if item.type_ == BudgetItemTypeEnum.INCOME])
                   for category in self.categories)

    @cached_property
    def expense_items_count(self) -> int:
        """Count of expense items in all categories."""
        return sum(len([item for item in category.budget_items
                       if item.type_ == BudgetItemTypeEnum.EXPENSE])
                   for category in self.categories)

    @cached_property
    def total_items_count(self) -> int:
        """Count of all budget items in all categories."""
        return self.income_items_count + self.expense_items_count

    @cached_property
    def income_str(self) -> str:
        """Income sum string."""
        return f'{self.income:.2f}'

    @cached_property
    def expense(self) -> float:
        """Expense sum."""
        return sum(c.expense for c in self.categories)

    @cached_property
    def expense_str(self) -> str:
        """Expense sum string."""
        return f'{self.expense:.2f}'

    @cached_property
    def result(self) -> float:
        """Result."""
        return self.income - self.expense

    @cached_property
    def result_str(self) -> str:
        """Result string."""
        return f'{self.result:.2f}'

    @cached_property
    def income_legend_height(self) -> int:
        """Income legend height."""
        return self.income_items_count * self.LEGEND_ITEM_HEIGHT

    @cached_property
    def income_section_height(self) -> int:
        """Income section height."""
        return self.PIE_CHART_HEIGHT + self.income_legend_height

    @cached_property
    def income_categories(self) -> list[ReportCategory]:
        """Income categories."""
        return [c for c in self.categories if c.income]

    @cached_property
    def expense_legend_height(self) -> int:
        """Expense legend height."""
        return self.expense_items_count * self.LEGEND_ITEM_HEIGHT

    @cached_property
    def expense_section_height(self) -> int:
        """Expense section height."""
        return self.PIE_CHART_HEIGHT + self.expense_legend_height

    @cached_property
    def expense_categories(self) -> list[ReportCategory]:
        """Expense categories."""
        return [c for c in self.categories if c.expense]

    @cached_property
    def image_height(self) -> int:
        """Image height."""
        return self.income_section_height + self.expense_section_height

    @cached_property
    def income_title(self) -> str:
        return f'ДОХОДЫ {self.income_str} {self.valute.code}'

    @cached_property
    def expense_title(self) -> str:
        return f'РАСХОДЫ {self.expense_str} {self.valute.code}'

    @cached_property
    def max_category_name_length(self) -> int:
        """Max category name length."""
        return max((len(category.name) for category in self.categories), default=0)

    @cached_property
    def max_item_name_length(self) -> int:
        """Max item name length."""
        return max((len(item.name) for category in self.categories
                   for item in category.budget_items), default=0)

    async def _load_raw_data(self) -> None:
        """Load report data."""
        raw_data = await self.db.entry_repo.get_report(
            chat_id=self.chat_id, period0=self.period0, period1=self.period1)
        if not raw_data:
            raise NoRawDataError('no raw data found')
        self.raw_data = raw_data

    async def _convert_raw_data(self) -> None:
        """Convert raw data to report data."""
        data = defaultdict(dict)
        for category, budget_item, valute, amount in self.raw_data:
            converted_amount = amount * self.rates[valute.code]['avg']
            category_key = (category.id, category.name)
            if not data[category_key].get(budget_item.id):
                data[category_key][budget_item.id] = {
                    'name': budget_item.name,
                    'amount': converted_amount,
                    'category_name': category.name,
                    'type_': budget_item.type,
                }
            else:
                data[category_key][budget_item.id]['amount'] += converted_amount
        for category_key, budget_items in data.items():
            category = ReportCategory(
                name=category_key[1],
                budget_items=[ReportBudgetItem(**budget_item) for budget_item
                              in budget_items.values()],
            )
            self.categories.append(category)

    def _make_report_image(self) -> bytes:
        """Generate report image."""
        fig = plt.figure(figsize=(self.REPORT_IMAGE_WIDTH, self.image_height))
        gs = fig.add_gridspec(
            2, 1, height_ratios=[self.income_section_height, self.expense_section_height])
        for gs, categories, budget_item_type in (
            (gs[0], self.income_categories, BudgetItemTypeEnum.INCOME),
            (gs[1], self.expense_categories, BudgetItemTypeEnum.EXPENSE),
        ):
            self._create_section_plot(fig, gs, categories, budget_item_type)
        plt.tight_layout(pad=2.0)
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.2, dpi=100)
        plt.close(fig)
        image_bytes = buf.getvalue()
        buf.close()
        self.image = image_bytes

    def _create_section_plot(
            self, fig: plt.Figure, subplot_pos: gridspec.GridSpec,
            categories: list[ReportCategory],
            budget_item_type: BudgetItemTypeEnum, palette='deep') -> None:
        """Create a section of the report with title, pie chart and legend."""
        if not categories:
            return

        if budget_item_type == BudgetItemTypeEnum.INCOME:
            category_totals = [c.income for c in categories]
            legend_height = self.income_legend_height
            pie_labels = [f'{c.name} [{c.income_str}]' for c in categories]
            title = self.income_title
        else:
            category_totals = [c.expense for c in categories]
            legend_height = self.expense_legend_height
            pie_labels = [f'{c.name} [{c.expense_str}]' for c in categories]
            title = self.expense_title

        gs = gridspec.GridSpecFromSubplotSpec(
            2, 1, subplot_pos, height_ratios=[self.PIE_CHART_HEIGHT, legend_height])
        pie_ax = fig.add_subplot(gs[0])
        colors = sns.color_palette(palette, n_colors=len(categories))
        pie_ax.pie(
            category_totals, labels=pie_labels, colors=colors, autopct='%1.1f%%', startangle=90)
        pie_ax.set_title(title, fontsize=14, pad=20)
        legend_ax = fig.add_subplot(gs[1])
        legend_ax.axis('off')
        legend_items = []
        for category, color in zip(categories, colors):
            for item in [i for i in category.budget_items if i.type_ == budget_item_type]:
                formatted_text = (
                    f'{category.name.upper():{self.max_category_name_length}} '
                    f'| {item.name:{self.max_item_name_length}} | {item.amount_str}'
                )
                legend_items.append((color, formatted_text, item.amount))
        legend_items.sort(key=lambda x: x[2], reverse=True)

        item_count = len(legend_items)
        available_height = 0.9
        line_spacing = available_height / item_count if item_count > 0 else 0.05
        y_pos = 0.95
        for color, label, _ in legend_items:
            legend_ax.text(
                0.1, y_pos,
                label,
                fontsize=9,
                color=color,
                transform=legend_ax.transAxes,
                family='monospace',
            )
            y_pos -= line_spacing

    async def calculate(self) -> bytes:
        """Load, calculate data and make report image."""
        await self._load_valute()
        await self._load_raw_data()
        await self._load_rates(used_valutes=set(v for _, _, v, _ in self.raw_data))
        await self._convert_raw_data()
        self._make_report_image()


class ReportTotal(_ReportBase):
    """Report total."""

    period0: Optional[datetime.date] = None
    period1: Optional[datetime.date] = None
    income: Optional[float] = 0
    outcome: Optional[float] = 0
    balances: list[ChatBalance] = None
    fonds: list[ChatFond] = None
    debts: list[ChatDebt] = None
    image: Optional[bytes] = None

    COLORS = {
        'gray': (0.4, 0.4, 0.4, 1),
        'gray_light': (0.8, 0.8, 0.8, 1.0),
        'black': (0.0, 0.0, 0.0, 1.0),
        'green': (0.2, 0.8, 0.2, 1),
        'red': (0.8, 0.2, 0.2, 1),
        'blue': (0.2, 0.2, 0.8, 1),
        'orange': (1.0, 0.5, 0.0, 1.0),
    }

    IMAGE_LINE_HEIGHT = 0.12

    def __init__(self, db: 'DatabaseAccessor', chat_id: int, valute_code: str,
                 balances: list[ChatBalance], fonds: list[ChatFond],
                 debts: list[ChatDebt]) -> None:
        """Init Total report."""
        super().__init__(db=db, chat_id=chat_id, valute_code=valute_code)
        self.balances = balances
        self.fonds = fonds
        self.debts = debts

    @property
    def title(self) -> str:
        """Report title."""
        return f'ОТЧЕТ {self.period0.isoformat()} - {self.period1.isoformat()} в {self.valute.code}'

    @property
    def balance(self) -> float:
        """Balance."""
        total = 0
        for balance in self.balances or []:
            rate = self.rates[balance.valute.code]['avg']
            total += balance.amount * rate
        return total

    @property
    def balance_cur(self) -> float:
        """Balance."""
        total = 0
        for balance in self.balances or []:
            rate = self.rates[balance.valute.code]['cur']
            total += balance.amount * rate
        return total

    @property
    def fond(self) -> float:
        """Fond."""
        total = 0
        for fond in self.fonds or []:
            rate = self.rates[fond.valute.code]['avg']
            total += fond.amount * rate
        return total

    @property
    def fond_cur(self) -> float:
        """Fond."""
        total = 0
        for fond in self.fonds or []:
            rate = self.rates[fond.valute.code]['cur']
            total += fond.amount * rate
        return total

    @property
    def debt(self) -> float:
        """Debt."""
        total = 0
        for debt in self.debts or []:
            rate = self.rates[debt.valute.code]['avg']
            total += debt.amount * rate
        return total

    @property
    def debt_cur(self) -> float:
        """Debt."""
        total = 0
        for debt in self.debts or []:
            rate = self.rates[debt.valute.code]['cur']
            total += debt.amount * rate
        return total

    @property
    def total_result(self) -> float:
        """Total result."""
        return self.income - self.outcome

    @property
    def unregistered_amount(self) -> float:
        """Unregistered amount."""
        return self.balance - self.total_result

    @property
    def unregistered_amount_cur(self) -> float:
        """Unregistered amount."""
        return self.balance_cur - self.total_result

    @property
    def result_lines(self) -> list[tuple[[str, float]]]:
        """Result lines."""
        colors = self.COLORS
        lines = [
            ('доходы (I)', self.income, None, None, colors['gray']),
            ('расходы (O)', self.outcome, None, None, colors['gray']),
            ('I - O (R)', self.total_result, None, None, colors['blue']),
        ]
        return lines

    @property
    def headers(self) -> tuple[str]:
        """Headers."""
        return (
            'Название', 'По среднему курсу', 'По текущему курсу', 'В валюте статьи',
            self.COLORS['black'])

    def get_balance_fond_debt_lines(
            self, items: Literal['balance', 'fond', 'debt']) -> list[tuple[str, float, float, str]]:
        """Balance, fond and debt lines."""
        lines = []
        for item in getattr(self, items, []):
            valute_code = item.valute.code
            amount = item.amount
            rate = self.rates[valute_code]['avg']
            rate_cur = self.rates[valute_code]['cur']
            amount_avg, amount_cur = amount * rate, amount * rate_cur
            line = (
                f'{item.name} ({valute_code})', amount_avg, amount_cur, amount, self.COLORS['gray'])
            lines.append(line)
        return lines

    @cached_property
    def report_lines(self) -> list[tuple[[str, float]]]:
        """Report lines."""
        colors = self.COLORS
        lines = [(self.title, None, None, None, colors['black'])]
        lines += [self.headers]
        lines += [('Результаты', None, None, None, colors['gray_light'])]
        lines += self.result_lines
        lines += [('Балансы', None, None, None, colors['gray_light'])]
        lines += self.get_balance_fond_debt_lines('balances')
        lines += [('итого балансы (B)', self.balance, self.balance_cur, None, colors['blue'])]
        label = 'доходы' if self.unregistered_amount > 0 else 'расходы'
        color = colors['red'] if self.unregistered_amount != 0 else colors['gray']
        lines += [(
            f'не учтены {label} (B - R)', self.unregistered_amount, self.unregistered_amount_cur,
            None, color)]
        lines += [('Фонды', None, None, None, colors['gray_light'])]
        lines += self.get_balance_fond_debt_lines('fonds')
        minus_fond = self.total_result - self.fond
        minus_fond_cur = self.total_result - self.fond_cur
        lines += [('итого фонды (F)', self.fond, self.fond_cur, None, colors['blue'])]
        lines += [('за минусом фондов (R - F)', minus_fond, minus_fond_cur, None, colors['orange'])]
        lines += [('Долги', None, None, None, colors['gray_light'])]
        lines += self.get_balance_fond_debt_lines('debts')
        lines += [('итого долги (D)', self.debt, self.debt_cur, None, colors['blue'])]
        minus_debt = self.total_result - self.debt
        minus_debt_cur = self.total_result - self.debt_cur
        lines += [('за минусом долга (R - D)', minus_debt, minus_debt_cur, None, colors['orange'])]
        minus_fond_debt = minus_fond - self.debt
        minus_fond_debt_cur = minus_fond_cur - self.debt_cur
        color = colors['green'] if minus_fond_debt > 0 else colors['red']
        lines += [(
            'за минусом фондов и долга (R - F - D)', minus_fond_debt, minus_fond_debt_cur, None,
            color)]
        return lines

    @cached_property
    def image_height(self) -> int:
        """Image height."""
        title_row = 1
        space_rows = len([
            i for i in self.report_lines if
            i[1] is None and i[2] is None and i[3] is None
        ]) - title_row
        return (
            self.IMAGE_LINE_HEIGHT
            * (len(self.report_lines) + space_rows))

    async def calculate(self) -> Optional[bytes]:
        """Calculate and make report image."""
        await self._load_valute()
        await self._load_period()
        used_valutes = await self.db.entry_repo.get_chat_entries_valutes(chat_id=self.chat_id)
        await self._load_rates(used_valutes=used_valutes)
        await self._calculate_entries()
        self._make_report_image()

    async def load_rates(self) -> None:
        """Load rates."""
        await self._load_valute()
        await self._load_period()
        used_valutes = await self.db.entry_repo.get_chat_entries_valutes(chat_id=self.chat_id)
        await self._load_rates(used_valutes=used_valutes)

    async def _load_period(self) -> None:
        """Find max and min entries date."""
        period = await self.db.entry_repo.get_chat_entries_period(chat_id=self.chat_id)
        if not period or not all(period):
            raise NoRawDataError('no data for report')
        self.period0 = period[0].date()
        self.period1 = period[1].date()

    async def _calculate_entries(self) -> None:
        """Calculate income and outcome in report valute."""
        income = 0
        outcome = 0
        async for row in self.db.entry_repo.iterate_chat_entries(chat_id=self.chat_id):
            entry_type, amount, valute_code = row
            rate = self.rates[valute_code]['avg']
            if entry_type == BudgetItemTypeEnum.INCOME:
                income += amount * rate
            else:
                outcome += amount * rate
        self.income, self.outcome = income, outcome

    def _make_report_image(self) -> bytes:
        """Make report image."""
        title_line = self.report_lines[0]
        headers_line = self.report_lines[1]
        no_title_lines = self.report_lines[1:]
        no_title_no_header_lines = self.report_lines[2:]
        label_width = max(len(label) for label, *_ in no_title_lines)
        column_1_width = max(len(str(amount)) for _, amount, *_ in no_title_lines if amount)
        column_2_width = max(len(str(amount)) for _, _, amount, *_ in no_title_lines if amount)
        column_3_width = max(len(str(amount)) for _, _, _, amount, _ in no_title_lines if amount)
        title_line_str = title_line[0]
        title_color = title_line[-1]
        title_font_size = 14
        row_font_size = 13

        fig, ax = plt.subplots(figsize=(self.REPORT_IMAGE_WIDTH, self.image_height))
        ax.axis('off')

        y = self.image_height - self.IMAGE_LINE_HEIGHT
        ax.text(
            0, y, title_line_str, fontsize=title_font_size, va='center', ha='left',
            family=self.REPORT_TEXT_FAMILY, color=title_color)
        y -= self.IMAGE_LINE_HEIGHT * 2

        headers_label, headers_col1, headers_col2, headers_col3, headers_color = headers_line
        headers_text = (
            f'{headers_label:<{label_width}} | '
            f'{headers_col1:<{column_1_width}} | '
            f'{headers_col2:<{column_2_width}} | '
            f'{headers_col3:<{column_3_width}}'
        )
        ax.text(
            0, y, headers_text, fontsize=row_font_size, va='center', ha='left',
            family=self.REPORT_TEXT_FAMILY, color=headers_color, weight='bold')
        y -= self.IMAGE_LINE_HEIGHT

        for i, (
            label, avr_amount, cur_amount, valute_amount, color,
        ) in enumerate(no_title_no_header_lines):
            text = f'{label:<{label_width}}'
            is_subtitle = avr_amount is None and cur_amount is None and valute_amount is None
            if is_subtitle:
                if i > 0:
                    y -= self.IMAGE_LINE_HEIGHT
                text = text.upper()
                ax.text(
                    0, y, text, fontsize=row_font_size, va='center', ha='left',
                    family=self.REPORT_TEXT_FAMILY, color=color)
            else:
                text = [text]
                for value, width in zip(
                    [avr_amount, cur_amount, valute_amount],
                    [column_1_width, column_2_width, column_3_width]
                ):
                    value_s = f'{value:>{width}.2f}' if value is not None else f'{"":<{width}}'
                    text.append(value_s)
                text = ' | '.join(text)
                ax.text(
                    0, y, text, fontsize=row_font_size, va='center', ha='left',
                    family=self.REPORT_TEXT_FAMILY, color=color)
            y -= self.IMAGE_LINE_HEIGHT

        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.2, dpi=100)
        plt.close(fig)
        image_bytes = buf.getvalue()
        buf.close()
        self.image = image_bytes
