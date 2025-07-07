from typing import Optional

from app.accountant.report import Report
from app.constants import MONTHS_MAPPER, USD_CODE
from app.db_service.models import TGChat, TGUser, TGUserState
from app.tg_service import api as tg_api
from app.tg_service.schemas import (
    EditMessageTextResponseSchema,
    SendMessageResponseSchema,
    SendPhotoResponseSchema,
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
    """Actions with choosed month."""
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
        report = Report(USD_CODE, chat.id, year, month, self.db)
        image = await report.calculate()
        month_name = MONTHS_MAPPER[month]
        text = REPORT_RESULT.format(year=year, month=month_name)
        keyboard = self.editor.get_hide_keyboard()
        if image:
            await self.call_tg(
                tg_api.DeleteMessage, chat_id=chat.tg_id, message_id=callback.message.message_id)
            delete_also = []
            params = dict(chat_id=chat.tg_id, files=dict(photo=image))
            task = await self.call_tg(tg_api.SendPhoto, **params)
            await task.event.wait()
            response: Optional[SendPhotoResponseSchema] = task.response
            if response and response.result:
                delete_also.append(response.result.message_id)

            text = '\n\n'.join([text, f'ДОХОД - РАСХОД: {report.result_str}'])
            keyboard = self.editor.get_hide_keyboard(delete_also=delete_also)
            await self.call_tg(
                tg_api.SendMessage, chat_id=chat.tg_id, text=text, reply_markup=keyboard)
            await self.set_state(user, state, MessageHandlerEnum.DEFAULT, {})
