from collections import defaultdict
from statistics import geometric_mean
from typing import TYPE_CHECKING, Optional

from app.constants import MONTHS_MAPPER, USD_CODE, USDT_CODE, VALUTE_SUBSTITUTES
from app.db_service.enums import BudgetItemTypeEnum
from app.db_service.models import BudgetItem, Category, TGChat, TGUser, TGUserState, Valute
from app.tg_service import api as tg_api
from app.tg_service.schemas import (
    EditMessageTextResponseSchema,
    SendMessageResponseSchema,
    SendPhotoResponseSchema,
    TGCallbackQuerySchema,
    TGMessageSchema,
)
from app.utils import make_pie_chart

from ..enums import CallbackHandlerEnum, MessageHandlerEnum
from ..messages import REPORT_NO_ENTRIES, REPORT_RESULT, REPORT_SELECT_MONTH, REPORT_SELECT_YEAR
from .base import CallbackHandler, CommandHandler


if TYPE_CHECKING:
    from app.db_service.repository import DatabaseAccessor


RATE_PRECISION = 6


class ReportHandler(CommandHandler):
    async def handle(
        self,
        *,
        chat: TGChat,
        message: TGMessageSchema,
        user: TGUser,
        state: Optional[TGUserState],
        **_,
    ) -> None:
        await self.delete_message(message)
        years = await self.db.entry_repo.get_years(chat_id=chat.id)

        if not years:
            text = REPORT_NO_ENTRIES
            keyboard = self.editor.get_hide_keyboard()
            await self.send_message(chat, None, text, keyboard)
            await self.set_state(user, state, MessageHandlerEnum.DEFAULT, {})
        elif len(years) == 1:
            year = years[0]
            text = REPORT_SELECT_MONTH.format(year=year)
            months = await self.db.entry_repo.get_months(chat_id=chat.id, year=year)
            keyboard = self.editor.get_months_keyboard(months)
            task = await self.send_message(chat, None, text, keyboard)
            await task.event.wait()
            response: Optional[SendMessageResponseSchema] = task.response
            if response:
                data_raw = dict(message_id=response.result.message_id, year=year)
                await self.set_state(user, state, CallbackHandlerEnum.REPORT_SELECT_MONTH, data_raw)
        else:
            text = REPORT_SELECT_YEAR
            keyboard = self.editor.get_years_keyboard(years)
            task = await self.send_message(chat, None, text, keyboard)
            await task.event.wait()
            response: Optional[SendMessageResponseSchema] = task.response
            if response:
                data_raw = dict(message_id=response.result.message_id)
                await self.set_state(user, state, CallbackHandlerEnum.REPORT_SELECT_YEAR, data_raw)


class ReportSelectYearHandler(CallbackHandler):
    async def handle(
        self,
        *,
        chat: TGChat,
        callback: TGCallbackQuerySchema,
        user: TGUser,
        state: Optional[TGUserState],
        **_,
    ) -> None:
        await super().handle(callback=callback, state=state, **_)
        year = int(callback.data)
        text = REPORT_SELECT_MONTH.format(year=year)
        months = await self.db.entry_repo.get_months(chat_id=chat.id, year=year)
        keyboard = self.editor.get_months_keyboard(months)
        task = await self.edit_message(chat.tg_id, callback.message.message_id, text, keyboard)
        await task.event.wait()
        response: Optional[EditMessageTextResponseSchema] = task.response
        if response:
            data_raw = dict(message_id=callback.message.message_id, year=year)
            await self.set_state(user, state, CallbackHandlerEnum.REPORT_SELECT_MONTH, data_raw)


class ReportSelectMonthHandler(CallbackHandler):
    async def handle(
        self,
        *,
        chat: TGChat,
        callback: TGCallbackQuerySchema,
        user: TGUser,
        state: Optional[TGUserState],
        **_,
    ) -> None:
        await super().handle(callback=callback, state=state, **_)
        year = state.data.year
        month = int(callback.data)
        month_name = MONTHS_MAPPER[month]
        text = REPORT_RESULT.format(year=year, month=month_name)
        keyboard = self.editor.get_hide_keyboard()
        report_data = await self.db.entry_repo.get_report(chat_id=chat.id, year=year, month=month)

        report_valute: Optional[Valute] = await self.db.valute_repo.get_by_code(USD_CODE)
        rates = None
        if report_valute:
            substitutes = VALUTE_SUBSTITUTES.get(report_valute.code, [])
            rates_to_find = set(valute for valute
                                in [valute for _, _, valute, _ in report_data]
                                if (valute.code != report_valute.code)
                                and valute.code not in substitutes)
            rates = await _get_valute_rates(self.db, report_valute, rates_to_find, month)
            if rates and substitutes:
                rates.update(dict.fromkeys(substitutes, 1))

        images, fin_result = _make_image_report(report_data, report_valute, rates)
        if images and fin_result:
            await self.call_tg(tg_api.DeleteMessage, chat_id=chat.tg_id, message_id=callback.message.message_id)
            delete_also = []
            for image in images:
                params = dict(chat_id=chat.tg_id, files=dict(photo=image))
                task = await self.call_tg(tg_api.SendPhoto, **params)
                await task.event.wait()
                response: Optional[SendPhotoResponseSchema] = task.response
                if response and response.result:
                    delete_also.append(response.result.message_id)

            text = '\n\n'.join([text, f'Результат: {fin_result:.2f} {report_valute.code}'])
            keyboard = self.editor.get_hide_keyboard(delete_also=delete_also)
            await self.call_tg(tg_api.SendMessage, chat_id=chat.tg_id, text=text, reply_markup=keyboard)
            await self.set_state(user, state, MessageHandlerEnum.DEFAULT, {})

        else:
            report_text = _make_text_report(report_data, report_valute, rates)
            text += '\n\n' + report_text
            await self.edit_message(chat.tg_id, callback.message.message_id, text, keyboard)
            await self.set_state(user, state, MessageHandlerEnum.DEFAULT, {})


def _make_text_report(
    report_data: list[tuple[Category, BudgetItem, Valute, int]],
    report_valute: Optional[Valute] = None,
    rates: Optional[dict[str, float]] = None,
) -> str:
    types = {
        BudgetItemTypeEnum.INCOME.value: 'доходы',
        BudgetItemTypeEnum.EXPENSE.value: 'расходы',
    }

    mapper = _map_report_data(report_data, report_valute, rates)

    totals = dict()
    lines = []
    for item_type, data in mapper.items():
        type_total = 0
        type_lines = []
        for category, items in data.items():
            category_total = 0
            category_lines = []
            for budget_item, item_data in items.items():
                for valute, amount in item_data.items():
                    amount_line = '{:.2f}'.format(amount)
                    line = f'    {budget_item} - {amount_line}'
                    if not rates:
                        line += f' - {valute}'
                    category_lines.append(line)
                    category_total += amount
            category_line = f'  {category.capitalize()}'
            if rates:
                category_line += f' - {category_total:.2f}'
            type_lines.append(category_line)
            type_lines.extend(category_lines)
            type_total += category_total
        type_line = types[item_type].upper()
        if rates:
            type_line += f' - {type_total:.2f}'
        lines.append(type_line)
        lines.extend(type_lines)
        lines.append('')
        totals[item_type] = type_total

    if rates:
        expensas = totals.get(BudgetItemTypeEnum.EXPENSE, 0)
        incomes = totals.get(BudgetItemTypeEnum.INCOME, 0)
        total_line = f'Результат: {incomes - expensas:.2f} {report_valute.code}'
        lines.append(total_line)

    return '\n'.join(lines)


def _map_report_data(
    report_data: list[tuple[Category, BudgetItem, Valute, int]],
    report_valute: Optional[Valute] = None,
    rates: Optional[dict[str, float]] = None,
) -> dict:
    mapper = {
        BudgetItemTypeEnum.INCOME.value: defaultdict(lambda: defaultdict(lambda: defaultdict(int))),
        BudgetItemTypeEnum.EXPENSE.value: defaultdict(lambda: defaultdict(lambda: defaultdict(int))),
    }
    for category, budget_item, valute, amount in report_data:
        code = report_valute.code if rates else valute.code
        if rates and valute.code != report_valute.code:
            amount = amount * rates.get(valute.code)
        mapper[budget_item.type][category.name][budget_item.name][code] += amount
    return mapper


async def _get_valute_rates(
    db: 'DatabaseAccessor', target_valute: Valute, rates_to_find: set[Valute], month: int,
) -> Optional[dict[str, float]]:
    rates = {}
    usd = await db.valute_repo.get_by_code(USD_CODE)

    for valute in rates_to_find:
        direct = await _get_exchange_rate(db, valute, target_valute, month)
        if direct:
            rates[valute.code] = direct
            continue
        valute_to_usd = await _get_exchange_rate(db, valute, usd, month)
        usd_to_target = await _get_exchange_rate(db, usd, valute, month)
        if valute_to_usd and usd_to_target:
            rate = round(valute_to_usd * usd_to_target, 6)
            rates[valute.code] = rate
            continue
        valute_to_usd = await _get_daily_rate(db, valute, usd, month)
        if target_valute.code in [USD_CODE, USDT_CODE]:
            usd_to_target = 1
        else:
            usd_to_target = await _get_daily_rate(db, usd, target_valute, month)
        if valute_to_usd and usd_to_target:
            rate = round(valute_to_usd * usd_to_target, 6)
            rates[valute.code] = rate

    if sorted(v.code for v in rates_to_find) != sorted(rates.keys()):
        return None

    return rates


async def _get_exchange_rate(
    db: 'DatabaseAccessor',
    valute_from: Valute,
    valute_to: Valute,
    month: int,
) -> Optional[float]:
    rates = []
    from_codes = [valute_from.code] + VALUTE_SUBSTITUTES.get(valute_from.code, [])
    to_codes = [valute_to.code] + VALUTE_SUBSTITUTES.get(valute_to.code, [])
    exchanges = await db.valute_exchange_repo.get_pair_exchanges(from_codes, to_codes, month)
    for exchange in exchanges:
        rate = round(exchange.valute_to_amount / exchange.valute_from_amount, RATE_PRECISION)
        rates.append(rate)
    exchanges = await db.valute_exchange_repo.get_pair_exchanges(to_codes, from_codes, month)
    for exchange in exchanges:
        rate = round(exchange.valute_from_amount / exchange.valute_to_amount, RATE_PRECISION)
        rates.append(rate)
    return geometric_mean(rates) if rates else None


async def _get_daily_rate(
    db: 'DatabaseAccessor',
    valute_from: Valute,
    valute_to: Valute,
    month: int,
) -> Optional[float]:
    rates = []
    from_codes = [valute_from.code] + VALUTE_SUBSTITUTES.get(valute_from.code, [])
    to_codes = [valute_to.code] + VALUTE_SUBSTITUTES.get(valute_to.code, [])
    daily_rates = await db.valute_rate_repo.get_month_rates(from_codes, to_codes, month)
    for rate in daily_rates:
        rates.append(rate.rate)
    daily_rates = await db.valute_rate_repo.get_month_rates(to_codes, from_codes, month)
    for rate in daily_rates:
        rate = round(1 / rate.rate, RATE_PRECISION)
        rates.append(rate)
    return geometric_mean(rates) if rates else None


def _make_image_report(
    report_data: list[tuple[Category, BudgetItem, Valute, int]],
    report_valute: Optional[Valute] = None,
    rates: Optional[dict[str, float]] = None,
) -> tuple[Optional[list[bytes]], Optional[float]]:
    if not rates:
        return None, None

    mapper = _map_report_data(report_data, report_valute, rates)
    ru_types = {
        BudgetItemTypeEnum.INCOME.value: 'ДОХОДЫ',
        BudgetItemTypeEnum.EXPENSE.value: 'РАСХОДЫ',
    }
    images = []

    totals = dict()
    for item_type, data in mapper.items():
        total = 0
        chart_labels = []
        chart_data = []
        for category, items in data.items():
            for budget_item, item_data in items.items():
                for _, amount in item_data.items():
                    total += amount
                    chart_labels.append(f'{category} - {budget_item}')
                    chart_data.append(amount)

        legend_title = f'{ru_types.get(item_type)} {total:.2f} {report_valute.code}'
        image = make_pie_chart(chart_labels, chart_data, title=None, legend_title=legend_title)
        images.append(image)
        totals[item_type] = total

    fin_result = totals.get(BudgetItemTypeEnum.INCOME.value, 0) - totals.get(BudgetItemTypeEnum.EXPENSE.value, 0)

    return images, fin_result
