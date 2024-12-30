from collections import defaultdict
from typing import Optional

from app.constants import MONTHS_MAPPER
from app.db_service.enums import BudgetItemTypeEnum
from app.db_service.models import BudgetItem, Category, TGChat, TGUser, TGUserState, Valute
from app.tg_service.schemas import (
    EditMessageTextResponseSchema,
    SendMessageResponseSchema,
    TGCallbackQuerySchema,
    TGMessageSchema,
)

from ..enums import CallbackHandlerEnum, MessageHandlerEnum
from ..messages import REPORT_NO_ENTRIES, REPORT_RESULT, REPORT_SELECT_MONTH, REPORT_SELECT_YEAR
from .base import CallbackHandler, CommandHandler


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
        report_text = _make_report(report_data)
        text += '\n\n' + report_text
        await self.edit_message(chat.tg_id, callback.message.message_id, text, keyboard)
        await self.set_state(user, state, MessageHandlerEnum.DEFAULT, {})


def _make_report(report_data: list[tuple[Category, BudgetItem, Valute, int]]) -> str:
    types = {
        BudgetItemTypeEnum.INCOME.value: 'доходы',
        BudgetItemTypeEnum.EXPENSE.value: 'расходы',
    }

    mapper = {
        BudgetItemTypeEnum.INCOME.value: defaultdict(dict),
        BudgetItemTypeEnum.EXPENSE.value: defaultdict(dict),
    }
    for category, budget_item, valute, amount in report_data:
        mapper[budget_item.type][category.name][budget_item.name] = (amount, valute.code)

    lines = []
    for type, data in mapper.items():
        lines.append(types[type].upper())
        for category, items in data.items():
            lines.append(f'  {category.capitalize()}')
            for budget_item, item_details in items.items():
                amount, valute = item_details
                line = f'    {budget_item} - {amount} - {valute}'
                lines.append(line)

    return '\n'.join(lines)
