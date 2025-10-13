import calendar
import datetime
from typing import Optional

from app.accountant.report import Report, ReportError, ReportTotal
from app.constants import MONTHS_MAPPER, USD_CODE
from app.tg_service.schemas import SendPhotoResponseSchema

from ..enums import CallbackHandlerEnum, CommandHadlerEnum, MessageHandlerEnum
from ..messages import REPORT_ERROR, REPORT_NO_ENTRIES, REPORT_RESULT, REPORT_SELECT_MONTH, REPORT_SELECT_YEAR
from ..registry import handler
from .base import CallbackHandler, CommandHandler


class ReportHandlerMixin:
    """Common report methods."""

    async def _report_current(self):
        """Process current state report."""
        report = ReportTotal(
            db=self.db, chat_id=self.chat.id, valute_code=USD_CODE, balances=self.chat.balances,
            fonds=self.chat.fonds, debts=self.chat.debts)
        try:
            await report.calculate()
            if not report.image:
                raise ReportError('report image not found')
        except ReportError:
            keyboard = self.editor.get_hide_keyboard()
            await self.send_message(text=REPORT_ERROR, reply_markup=keyboard)
            raise

        keyboard = self.editor.get_hide_keyboard()
        await self.send_photo(photo=report.image, reply_markup=keyboard)


@handler(CommandHadlerEnum.REPORT)
class ReportHandler(CommandHandler):
    """Process click on /report command."""

    async def handle(self) -> None:
        """Handle report command."""
        chat = self.chat

        await self.delete_income_messages()
        years = await self.db.entry_repo.get_years(chat_id=chat.id)

        if not years:
            text = REPORT_NO_ENTRIES
            keyboard = self.editor.get_hide_keyboard()
            await self.send_message(text, keyboard)
            await self.set_state(MessageHandlerEnum.DEFAULT, {})
        elif len(years) == 1:
            year = years[0]
            text = REPORT_SELECT_MONTH.format(year=year)
            months = await self.db.entry_repo.get_months(chat_id=chat.id, year=year)
            keyboard = self.editor.get_months_keyboard(months, add_current_btn=True)
            task = await self.send_message(text, keyboard)
            await self.wait_task_result(
                task, CallbackHandlerEnum.REPORT_SELECT_MONTH, state_data={'year': year},
                response_to_state={'message_id'})
        else:
            text = REPORT_SELECT_YEAR
            keyboard = self.editor.get_years_keyboard(years, add_current_btn=True)
            task = await self.send_message(text, keyboard)
            await self.wait_task_result(
                task, CallbackHandlerEnum.REPORT_SELECT_YEAR, response_to_state={'message_id'})


@handler(CallbackHandlerEnum.REPORT_SELECT_YEAR)
class ReportSelectYearHandler(CallbackHandler, ReportHandlerMixin):
    """Process click on year."""

    async def handle(self) -> None:
        """Handle report select year."""
        callback = self.update
        chat = self.chat

        await super().handle()
        choice = callback.data
        if choice == 'current':
            await self.delete_income_messages()
            await self._report_current()
        else:
            year = int(choice)
            text = REPORT_SELECT_MONTH.format(year=year)
            months = await self.db.entry_repo.get_months(chat_id=chat.id, year=year)
            keyboard = self.editor.get_months_keyboard(months)
            task = await self.edit_message(callback.message.message_id, text, keyboard)
            await self.wait_task_result(
                task, CallbackHandlerEnum.REPORT_SELECT_MONTH, state_data={'year': year},
                response_to_state={'message_id'})


@handler(CallbackHandlerEnum.REPORT_SELECT_MONTH)
class ReportSelectMonthHandler(CallbackHandler, ReportHandlerMixin):
    """Process click on month."""

    async def handle(self) -> None:
        """Handle report select month."""
        await super().handle()
        callback = self.update
        chat = self.chat

        choice = callback.data
        if choice == 'current':
            await self.delete_income_messages()
            await self._report_current()
        else:
            # TODO: make solo image
            choice = int(choice)
            year = self.state.data.year
            month = int(callback.data)
            period0 = datetime.date(year, month, 1)
            last_day = calendar.monthrange(year, month)[1]
            period1 = datetime.date(year, month, last_day)
            report = Report(USD_CODE, chat.id, period0, period1, self.db)
            await report.calculate()
            image = report.image
            month_name = MONTHS_MAPPER[month]
            text = REPORT_RESULT.format(year=year, month=month_name)
            keyboard = self.editor.get_hide_keyboard()
            await self.delete_income_messages()
            delete_also = []
            task = await self.send_photo(photo=image)
            await task.event.wait()
            response: Optional[SendPhotoResponseSchema] = task.response
            if response and response.result:
                delete_also.append(response.result.message_id)

            text = '\n\n'.join([text, f'ДОХОД - РАСХОД: {report.result_str}'])
            keyboard = self.editor.get_hide_keyboard(delete_also=delete_also)
            await self.send_message(text, keyboard)
            await self.set_state(MessageHandlerEnum.DEFAULT, {})
