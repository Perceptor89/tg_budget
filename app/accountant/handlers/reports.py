from typing import Optional

from app.accountant.report import Report
from app.constants import MONTHS_MAPPER, USD_CODE
from app.tg_service.schemas import SendPhotoResponseSchema

from ..enums import CallbackHandlerEnum, MessageHandlerEnum
from ..messages import REPORT_NO_ENTRIES, REPORT_RESULT, REPORT_SELECT_MONTH, REPORT_SELECT_YEAR
from .base import CallbackHandler, CommandHandler


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
            keyboard = self.editor.get_months_keyboard(months)
            task = await self.send_message(text, keyboard)
            await self.wait_task_result(
                task, CallbackHandlerEnum.REPORT_SELECT_MONTH, state_data={'year': year},
                response_to_state={'message_id'})
        else:
            text = REPORT_SELECT_YEAR
            keyboard = self.editor.get_years_keyboard(years)
            task = await self.send_message(text, keyboard)
            await self.wait_task_result(
                task, CallbackHandlerEnum.REPORT_SELECT_YEAR, response_to_state={'message_id'})


class ReportSelectYearHandler(CallbackHandler):
    """Process click on year."""

    async def handle(self) -> None:
        """Handle report select year."""
        callback = self.update
        chat = self.chat

        await super().handle()
        year = int(callback.data)
        text = REPORT_SELECT_MONTH.format(year=year)
        months = await self.db.entry_repo.get_months(chat_id=chat.id, year=year)
        keyboard = self.editor.get_months_keyboard(months)
        task = await self.edit_message(callback.message.message_id, text, keyboard)
        await self.wait_task_result(
            task, CallbackHandlerEnum.REPORT_SELECT_MONTH, state_data={'year': year},
            response_to_state={'message_id'})


class ReportSelectMonthHandler(CallbackHandler):
    """Process click on month."""

    async def handle(self) -> None:
        """Handle report select month."""
        await super().handle()
        callback = self.update
        chat = self.chat

        year = self.state.data.year
        month = int(callback.data)
        report = Report(USD_CODE, chat.id, year, month, self.db)
        image = await report.calculate()
        month_name = MONTHS_MAPPER[month]
        text = REPORT_RESULT.format(year=year, month=month_name)
        keyboard = self.editor.get_hide_keyboard()
        if image:
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
