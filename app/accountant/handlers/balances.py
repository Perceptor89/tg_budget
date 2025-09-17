from typing import Optional

from app import exceptoions, utils
from app.db_service.models import ChatBalance, Valute
from app.tg_service import schemas as tg_schemas

from .. import messages
from ..enums import CallbackHandlerEnum, MessageHandlerEnum
from .base import CallbackHandler, CommandHandler, MessageHandler


class BalanceCreateMixin:
    """Balance create mixin."""

    def get_state_balance_name(self) -> str:
        """Get balance from state."""
        if not (balance_name := self.state.data.balance_name):
            raise exceptoions.AccountantError('state balance_name not found')
        return balance_name

    def get_picked_balance(self, balance_name: Optional[str] = None) -> ChatBalance:
        """Get picked balance."""
        balance_name = balance_name or self.get_state_balance_name()
        if not (balance := [b for b in self.chat.balances if b.name == balance_name]):
            raise exceptoions.AccountantError(f'balance {balance_name} not found')
        return balance[0]


class BalanceCreateHandler(CommandHandler):
    """Balance create handler."""

    async def handle(self) -> None:
        """Process balance create command click."""
        await self.delete_income_messages()
        mention = self.editor.get_mention(self.user.username)
        text = messages.BALANCE_CREATE_NAME.format(mention)
        keyboard = tg_schemas.ForceReplySchema(
            input_field_placeholder=messages.BALANCE_CREATE_NAME_PLACEHOLDER)
        task = await self.send_message(text, keyboard)
        await self.wait_task_result(task, MessageHandlerEnum.BALANCE_CREATE_NAME,
                                    response_to_state={'message_id'})


class BalanceCreateNameHandler(MessageHandler):
    """Balance create name handler."""

    async def handle(self) -> None:
        """Process balance create name."""
        await super().handle()
        await self.delete_income_messages(delete_reply_to_msg=True)
        new_name = self.update.text
        chat = self.chat
        if [b for b in chat.balances if b.name.lower() == new_name.lower()]:
            mention = self.editor.get_mention(self.user.username)
            text = messages.BALANCE_CREATE_EXISTS_ERROR.format(new_name, mention)
            keyboard = tg_schemas.ForceReplySchema(
                input_field_placeholder=messages.BALANCE_CREATE_NAME_PLACEHOLDER)
            task = await self.send_message(text, keyboard)
            await self.wait_task_result(task, MessageHandlerEnum.BALANCE_CREATE_NAME,
                                        response_to_state={'message_id'})
        else:
            keyboard = self.editor.get_valute_keyboard(chat.valutes)
            text = messages.BALANCE_CREATE_VALUTE
            task = await self.send_message(text, keyboard)
            await self.wait_task_result(task, CallbackHandlerEnum.BALANCE_CREATE_VALUTE,
                                        state_data={'balance_name': new_name},
                                        response_to_state={'message_id'})


class BalanceCreateValuteHandler(CallbackHandler, BalanceCreateMixin):
    """Balance create valute handler."""

    async def handle(self) -> None:
        """Process balance create valute."""
        await super().handle()
        repo = self.db.chat_balance_repo
        await self.delete_income_messages()
        valute: Valute = await self.db.valute_repo.get_by_code(self.update.data)
        balance_name = self.get_state_balance_name()
        balance = ChatBalance(name=balance_name, chat_id=self.chat.id, valute_id=valute.id)
        await repo.create_item(balance)
        balance_info = f'{balance_name} | {balance.amount_str} {valute.code}'
        text = '\n\n'.join([
            messages.BALANCE_INFO.format(balance_info=balance_info),
            messages.BALANCE_CREATED,
        ])
        keyboard = self.editor.get_hide_keyboard()
        task = await self.send_message(text, keyboard)
        await self.wait_task_result(task, MessageHandlerEnum.DEFAULT, state_data={})


class BalanceListHandler(CommandHandler):
    """Balance list handler."""

    async def handle(self) -> None:
        """Process balance list command click."""
        await self.delete_income_messages()
        chat = self.chat
        balances: list[ChatBalance] = chat.balances
        if not balances:
            text = messages.BALANCE_LIST_NO_BALANCES
            keyboard = self.editor.get_hide_keyboard()
            await self.send_message(text, keyboard)
            await self.set_state(MessageHandlerEnum.DEFAULT, {})
        else:
            max_name = max(len(b.name) for b in balances)
            amounts = [b.amount_str for b in balances]
            max_amount = max(len(a) for a in amounts)
            lines = [f'`{b.get_info(max_name, max_amount)}`' for b in balances]
            text = messages.BALANCE_LIST.format('\n'.join(lines))
            keyboard = self.editor.get_hide_keyboard()
            task = await self.send_message(text, keyboard)
            await self.wait_task_result(task, MessageHandlerEnum.DEFAULT, {})


class BalanceSetHandler(CommandHandler):
    """Balance set amount handler."""

    async def handle(self) -> None:
        """Process balance set amount."""
        await self.delete_income_messages()
        text = messages.BALANCE_SET_CHOOSE_ONE
        keyboard = self.editor.create_inline_keyboard(
            buttons=[(b.name, b.name) for b in self.chat.balances],
            add_hide_button=True)
        task = await self.send_message(text, keyboard)
        await self.wait_task_result(task, CallbackHandlerEnum.BALANCE_SET_CHOOSE_ONE,
                                    response_to_state={'message_id'})


class BalanceSetChooseOneHandler(CallbackHandler, BalanceCreateMixin):
    """Balance set choose one handler."""

    async def handle(self) -> None:
        """Process picked balance."""
        await super().handle()
        picked_name = self.update.data
        balance = self.get_picked_balance(picked_name)
        original_message_id = self.update.message.message_id
        text = messages.BALANCE_SET_ENTER_AMOUNT_MAIN.format(balance_info=balance.info)
        await self.edit_message(original_message_id, text)
        text = messages.BALANCE_SET_ENTER_AMOUNT_REPLY.format(mention=self.user_mention)
        keyboard = tg_schemas.ForceReplySchema(
            input_field_placeholder=messages.BALANCE_SET_ENTER_AMOUNT_PLACEHOLDER)
        task = await self.send_message(text, keyboard)
        await self.wait_task_result(task, MessageHandlerEnum.BALANCE_SET_SAVE_AMOUNT,
                                    state_data={'main_message_id': original_message_id,
                                                'balance_name': balance.name},
                                    response_to_state={'message_id'})


class BalanceSetSaveAmountHandler(MessageHandler, BalanceCreateMixin):
    """Balance set save amount handler."""

    async def handle(self) -> None:
        """Process balance set save amount."""
        await super().handle()
        await self.delete_income_messages(delete_reply_to_msg=True)
        entered_amount = self.update.text
        balance = self.get_picked_balance()
        original_message_id = self.state.data.main_message_id
        try:
            amount = float(entered_amount)
        except ValueError:
            text = messages.BALANCE_SET_ENTER_AMOUNT_ERROR.format(
                mention=self.user_mention, entered_amount=entered_amount)
            keyboard = tg_schemas.ForceReplySchema(
                input_field_placeholder=messages.BALANCE_SET_ENTER_AMOUNT_PLACEHOLDER)
            task = await self.send_message(text, reply_markup=keyboard)
            await self.wait_task_result(task, MessageHandlerEnum.BALANCE_SET_SAVE_AMOUNT,
                                        state_data={'main_message_id': original_message_id,
                                                    'balance_name': balance.name},
                                        response_to_state={'message_id'})
        else:
            repo = self.db.chat_balance_repo
            balance.amount = amount
            balance.updated_at = utils.utcnow()
            balance: ChatBalance = await repo.update_item(balance)
            text = '\n\n'.join([
                messages.BALANCE_INFO.format(balance_info=balance.info),
                messages.BALANCE_SET_SAVED])
            keyboard = self.editor.get_hide_keyboard()
            task = await self.edit_message(original_message_id, text, keyboard)
            await self.wait_task_result(task, MessageHandlerEnum.DEFAULT, {})


class BalanceDeleteHandler(CommandHandler):
    """Balance delete handler."""

    async def handle(self) -> None:
        """Process balance delete command click."""
        # TODO: check existance
        await self.delete_income_messages()
        text = messages.BALANCE_DELETE_CHOOSE_ONE
        keyboard = self.editor.create_inline_keyboard(
            buttons=[(b.name, b.name) for b in self.chat.balances],
            add_hide_button=True)
        task = await self.send_message(text, keyboard)
        await self.wait_task_result(task, CallbackHandlerEnum.BALANCE_DELETE_CHOOSE_ONE,
                                    response_to_state={'message_id'})


class BalanceDeleteChooseOneHandler(CallbackHandler, BalanceCreateMixin):
    """Balance delete choose one handler."""

    async def handle(self) -> None:
        """Process picked balance."""
        await super().handle()
        picked_name = self.update.data
        balance = self.get_picked_balance(picked_name)
        original_message_id = self.update.message.message_id
        text = '\n\n'.join([
            messages.BALANCE_INFO.format(balance_info=balance.info),
            messages.BALANCE_DELETE_APPROVE,
        ])
        keyboard = self.editor.get_yes_no_keyboard()
        task = await self.edit_message(original_message_id, text, keyboard)
        await self.wait_task_result(task, CallbackHandlerEnum.BALANCE_DELETE_CONFIRM,
                                    state_data={'message_id': original_message_id,
                                                'balance_name': balance.name})


class BalanceDeleteConfirmHandler(CallbackHandler, BalanceCreateMixin):
    """Balance delete confirm handler."""

    async def handle(self) -> None:
        """Process balance delete confirm."""
        await super().handle()
        balance = self.get_picked_balance()
        decision = bool(int(self.update.data))
        if decision is True:
            repo = self.db.chat_balance_repo
            await repo.delete_item(balance)
            text = '\n\n'.join([
                messages.BALANCE_INFO.format(balance_info=balance.info),
                messages.BALANCE_DELETED,
            ])
            keyboard = self.editor.get_hide_keyboard()
            task = await self.edit_message(self.state.data.message_id, text, keyboard)
            await self.wait_task_result(task, MessageHandlerEnum.DEFAULT, {})
        else:
            await self.delete_income_messages()
            await self.set_state(MessageHandlerEnum.DEFAULT, {})
