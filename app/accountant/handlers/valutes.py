from app.accountant.enums import CommandHadlerEnum, MessageHandlerEnum
from app.accountant.handlers.base import CommandHandler
from app.accountant.messages import RATE_LIST_TITLE, REPORT_ERROR
from app.accountant.registry import handler
from app.accountant.report import ReportError, ReportTotal
from app.constants import USD_CODE, USDT_CODE


@handler(CommandHadlerEnum.RATE_LIST)
class RateListHandler(CommandHandler):
    """Process click on /rate_list command."""

    RATE_PRECISION = 4
    HEADERS = ['', '1 USD avg', 'rate', '1 USD cur', 'rate']

    async def handle(self) -> None:
        """Handle rate list command."""
        chat = self.chat

        await self.delete_income_messages()
        report = ReportTotal(
            db=self.db, chat_id=chat.id, valute_code=USD_CODE, balances=chat.balances,
            fonds=chat.fonds, debts=chat.debts)
        keyboard = self.editor.get_hide_keyboard()
        try:
            await report.load_rates()
        except ReportError:
            await self.send_message(text=REPORT_ERROR, reply_markup=keyboard)
            raise
        rates = report.rates
        lines = [RATE_LIST_TITLE]
        rate_list = []
        code_width = len(self.HEADERS[0])
        per_dollar_avg_width = len(self.HEADERS[1])
        per_dollar_cur_width = len(self.HEADERS[2])
        dollar_per_valute_avg_width = len(self.HEADERS[3])
        dollar_per_valute_cur_width = len(self.HEADERS[4])
        for code, rates in rates.items():
            if code in (USD_CODE, USDT_CODE):
                continue
            per_dollar_avg = 1 / rates['avg']
            per_dollar_cur = 1 / rates['cur']
            dollar_per_valute_avg = rates['avg']
            dollar_per_valute_cur = rates['cur']
            code_width = max(code_width, len(code))
            per_dollar_avg_width = max(
                per_dollar_avg_width,
                len(str(f'{per_dollar_avg:.{self.RATE_PRECISION}f}')))
            per_dollar_cur_width = max(
                per_dollar_cur_width,
                len(str(f'{per_dollar_cur:.{self.RATE_PRECISION}f}')))
            dollar_per_valute_avg_width = max(
                dollar_per_valute_avg_width,
                len(str(f'{dollar_per_valute_avg:.{self.RATE_PRECISION}f}')))
            dollar_per_valute_cur_width = max(
                dollar_per_valute_cur_width,
                len(str(f'{dollar_per_valute_cur:.{self.RATE_PRECISION}f}')))
            rate_list.append((
                code, per_dollar_avg, dollar_per_valute_avg, per_dollar_cur, dollar_per_valute_cur,
            ))
        headers = [
            f'`{self.HEADERS[0]:<{code_width}} | '
            f'{self.HEADERS[1]:<{per_dollar_avg_width}} | '
            f'{self.HEADERS[2]:<{dollar_per_valute_avg_width}} | '
            f'{self.HEADERS[3]:<{per_dollar_cur_width}} | '
            f'{self.HEADERS[4]:<{dollar_per_valute_cur_width}}`'
        ]
        rate_list = [
            f'`{code:<{code_width}} | '
            f'{per_dollar_avg:>{per_dollar_avg_width}.{self.RATE_PRECISION}f} | '
            f'{dollar_per_valute_avg:>{dollar_per_valute_avg_width}.{self.RATE_PRECISION}f} | '
            f'{per_dollar_cur:>{per_dollar_cur_width}.{self.RATE_PRECISION}f} | '
            f'{dollar_per_valute_cur:>{dollar_per_valute_cur_width}.{self.RATE_PRECISION}f}`'
            for code, per_dollar_avg, dollar_per_valute_avg, per_dollar_cur, dollar_per_valute_cur
            in rate_list
        ]
        lines.extend(headers + rate_list)
        text = '\n'.join(lines)
        task = await self.send_message(text, reply_markup=keyboard)
        await self.wait_task_result(task, MessageHandlerEnum.DEFAULT)
