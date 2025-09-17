from typing import Optional

from app import exceptoions, utils
from app.db_service.models import ChatDebt, Valute
from app.tg_service import schemas as tg_schemas

from .. import messages
from ..enums import CallbackHandlerEnum, MessageHandlerEnum
from .base import CallbackHandler, CommandHandler, MessageHandler


class DebtCreateMixin:
    """Debt create mixin."""

    def get_state_debt_name(self) -> str:
        """Get debt from state."""
        if not (debt_name := self.state.data.debt_name):
            raise exceptoions.AccountantError('state debt_name not found')
        return debt_name

    def get_picked_debt(self, debt_name: Optional[str] = None) -> ChatDebt:
        """Get picked debt."""
        debt_name = debt_name or self.get_state_debt_name()
        if not (debt := [d for d in self.chat.debts if d.name == debt_name]):
            raise exceptoions.AccountantError(f'debt {debt_name} not found')
        return debt[0]


class DebtCreateHandler(CommandHandler):
    """Debt create handler."""

    async def handle(self) -> None:
        """Process debt create command click."""
        await self.delete_income_messages()
        mention = self.editor.get_mention(self.user.username)
        text = messages.DEBT_CREATE_NAME.format(mention)
        keyboard = tg_schemas.ForceReplySchema(
            input_field_placeholder=messages.DEBT_CREATE_NAME_PLACEHOLDER)
        task = await self.send_message(text, keyboard)
        await self.wait_task_result(task, MessageHandlerEnum.DEBT_CREATE_NAME,
                                    response_to_state={'message_id'})


class DebtCreateNameHandler(MessageHandler):
    """Debt create name handler."""

    async def handle(self) -> None:
        """Process debt create name."""
        await super().handle()
        await self.delete_income_messages(delete_reply_to_msg=True)
        new_name = self.update.text
        chat = self.chat
        if [d for d in chat.debts if d.name.lower() == new_name.lower()]:
            mention = self.editor.get_mention(self.user.username)
            text = messages.DEBT_CREATE_EXISTS_ERROR.format(new_name, mention)
            keyboard = tg_schemas.ForceReplySchema(
                input_field_placeholder=messages.DEBT_CREATE_NAME_PLACEHOLDER)
            task = await self.send_message(text, keyboard)
            await self.wait_task_result(task, MessageHandlerEnum.DEBT_CREATE_NAME,
                                        response_to_state={'message_id'})
        else:
            keyboard = self.editor.get_valute_keyboard(chat.valutes)
            text = messages.DEBT_CREATE_VALUTE
            task = await self.send_message(text, keyboard)
            await self.wait_task_result(task, CallbackHandlerEnum.DEBT_CREATE_VALUTE,
                                        state_data={'debt_name': new_name},
                                        response_to_state={'message_id'})


class DebtCreateValuteHandler(CallbackHandler, DebtCreateMixin):
    """Debt create valute handler."""

    async def handle(self) -> None:
        """Process debt create valute."""
        await super().handle()
        repo = self.db.chat_debt_repo
        await self.delete_income_messages()
        valute: Valute = await self.db.valute_repo.get_by_code(self.update.data)
        debt_name = self.get_state_debt_name()
        debt = ChatDebt(name=debt_name, chat_id=self.chat.id, valute_id=valute.id)
        await repo.create_item(debt)
        debt_info = f'{debt_name} | {debt.amount_str} {valute.code}'
        text = '\n\n'.join([
            messages.DEBT_INFO.format(debt_info=debt_info),
            messages.DEBT_CREATED,
        ])
        keyboard = self.editor.get_hide_keyboard()
        task = await self.send_message(text, keyboard)
        await self.wait_task_result(task, MessageHandlerEnum.DEFAULT)


class DebtListHandler(CommandHandler):
    """Debt list handler."""

    async def handle(self) -> None:
        """Process debt list command click."""
        await self.delete_income_messages()
        chat = self.chat
        debts: list[ChatDebt] = chat.debts
        if not debts:
            text = messages.DEBT_LIST_NO_DEBTS
            keyboard = self.editor.get_hide_keyboard()
            await self.send_message(text, keyboard)
            await self.set_state(MessageHandlerEnum.DEFAULT, {})
        else:
            max_name = max(len(d.name) for d in debts)
            amounts = [d.amount_str for d in debts]
            max_amount = max(len(a) for a in amounts)
            lines = [f'`{d.get_info(max_name, max_amount)}`' for d in debts]
            text = messages.DEBT_LIST.format('\n'.join(lines))
            keyboard = self.editor.get_hide_keyboard()
            task = await self.send_message(text, keyboard)
            await self.wait_task_result(task, MessageHandlerEnum.DEFAULT)


class DebtSetHandler(CommandHandler):
    """Debt set amount handler."""

    async def handle(self) -> None:
        """Process debt set amount."""
        await self.delete_income_messages()
        text = messages.DEBT_SET_CHOOSE_ONE
        keyboard = self.editor.create_inline_keyboard(
            buttons=[(d.name, d.name) for d in self.chat.debts],
            add_hide_button=True)
        task = await self.send_message(text, keyboard)
        await self.wait_task_result(task, CallbackHandlerEnum.DEBT_SET_CHOOSE_ONE,
                                    response_to_state={'message_id'})


class DebtSetChooseOneHandler(CallbackHandler, DebtCreateMixin):
    """Debt set choose one handler."""

    async def handle(self) -> None:
        """Process picked debt."""
        await super().handle()
        picked_name = self.update.data
        debt = self.get_picked_debt(picked_name)
        original_message_id = self.update.message.message_id
        text = messages.DEBT_SET_ENTER_AMOUNT_MAIN.format(debt_name=debt.info)
        await self.edit_message(original_message_id, text)
        text = messages.DEBT_SET_ENTER_AMOUNT_REPLY.format(mention=self.user_mention)
        keyboard = tg_schemas.ForceReplySchema(
            input_field_placeholder=messages.DEBT_SET_ENTER_AMOUNT_PLACEHOLDER)
        task = await self.send_message(text, keyboard)
        await self.wait_task_result(task, MessageHandlerEnum.DEBT_SET_SAVE_AMOUNT,
                                    state_data={'main_message_id': original_message_id,
                                                'debt_name': debt.name},
                                    response_to_state={'message_id'})


class DebtSetSaveAmountHandler(MessageHandler, DebtCreateMixin):
    """Debt set save amount handler."""

    async def handle(self) -> None:
        """Process debt set save amount."""
        await super().handle()
        await self.delete_income_messages(delete_reply_to_msg=True)
        entered_amount = self.update.text
        debt = self.get_picked_debt()
        original_message_id = self.state.data.main_message_id
        try:
            amount = float(entered_amount)
        except ValueError:
            text = messages.DEBT_SET_ENTER_AMOUNT_ERROR.format(
                mention=self.user_mention, entered_amount=entered_amount)
            keyboard = tg_schemas.ForceReplySchema(
                input_field_placeholder=messages.DEBT_SET_ENTER_AMOUNT_PLACEHOLDER)
            task = await self.send_message(text, reply_markup=keyboard)
            await self.wait_task_result(task, MessageHandlerEnum.DEBT_SET_SAVE_AMOUNT,
                                        state_data={'main_message_id': original_message_id,
                                                    'debt_name': debt.name},
                                        response_to_state={'message_id'})
        else:
            repo = self.db.chat_debt_repo
            debt.amount = amount
            debt.updated_at = utils.utcnow()
            debt: ChatDebt = await repo.update_item(debt)
            text = '\n\n'.join([
                messages.DEBT_INFO.format(debt_info=debt.info),
                messages.DEBT_SET_SAVED])
            keyboard = self.editor.get_hide_keyboard()
            task = await self.edit_message(original_message_id, text, keyboard)
            await self.wait_task_result(task, MessageHandlerEnum.DEFAULT)


class DebtDeleteHandler(CommandHandler):
    """Debt delete handler."""

    async def handle(self) -> None:
        """Process debt delete command click."""
        # TODO: check existance
        await self.delete_income_messages()
        text = messages.DEBT_DELETE_CHOOSE_ONE
        keyboard = self.editor.create_inline_keyboard(
            buttons=[(d.name, d.name) for d in self.chat.debts],
            add_hide_button=True)
        task = await self.send_message(text, keyboard)
        await self.wait_task_result(task, CallbackHandlerEnum.DEBT_DELETE_CHOOSE_ONE,
                                    response_to_state={'message_id'})


class DebtDeleteChooseOneHandler(CallbackHandler, DebtCreateMixin):
    """Debt delete choose one handler."""

    async def handle(self) -> None:
        """Process picked debt."""
        await super().handle()
        picked_name = self.update.data
        debt = self.get_picked_debt(picked_name)
        original_message_id = self.update.message.message_id
        text = '\n\n'.join([
            messages.DEBT_INFO.format(debt_info=debt.info),
            messages.DEBT_DELETE_APPROVE,
        ])
        keyboard = self.editor.get_yes_no_keyboard()
        task = await self.edit_message(original_message_id, text, keyboard)
        await self.wait_task_result(task, CallbackHandlerEnum.DEBT_DELETE_CONFIRM,
                                    state_data={'message_id': original_message_id,
                                                'debt_name': debt.name})


class DebtDeleteConfirmHandler(CallbackHandler, DebtCreateMixin):
    """Debt delete confirm handler."""

    async def handle(self) -> None:
        """Process debt delete confirm."""
        await super().handle()
        debt = self.get_picked_debt()
        decision = bool(int(self.update.data))
        if decision is True:
            repo = self.db.chat_debt_repo
            await repo.delete_item(debt)
            text = '\n\n'.join([
                messages.DEBT_INFO.format(debt_info=debt.info),
                messages.DEBT_DELETED,
            ])
            keyboard = self.editor.get_hide_keyboard()
            task = await self.edit_message(self.state.data.message_id, text, keyboard)
            await self.wait_task_result(task, MessageHandlerEnum.DEFAULT)
        else:
            await self.delete_income_messages()
            await self.set_state(MessageHandlerEnum.DEFAULT, {})
