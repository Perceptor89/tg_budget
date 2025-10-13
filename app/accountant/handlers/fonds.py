from typing import Optional

from app import exceptoions, utils
from app.db_service.models import ChatFond, Valute
from app.tg_service import schemas as tg_schemas

from .. import messages
from ..enums import CallbackHandlerEnum, CommandHadlerEnum, MessageHandlerEnum
from ..registry import handler
from .base import CallbackHandler, CommandHandler, MessageHandler


class FondCreateMixin:
    """Fond create mixin."""

    def get_state_fond_name(self) -> str:
        """Get fond from state."""
        if not (fond_name := self.state.data.fond_name):
            raise exceptoions.AccountantError('state fond_name not found')
        return fond_name

    def get_picked_fond(self, fond_name: Optional[str] = None) -> ChatFond:
        """Get picked balance."""
        fond_name = fond_name or self.get_state_fond_name()
        if not (fond := [f for f in self.chat.fonds if f.name == fond_name]):
            raise exceptoions.AccountantError(f'balance {fond_name} not found')
        return fond[0]


@handler(CommandHadlerEnum.FOND_CREATE)
class FondCreateHandler(CommandHandler):
    """Fond create handler."""

    async def handle(self) -> None:
        """Process fond create command click."""
        await self.delete_income_messages()
        mention = self.editor.get_mention(self.user.username)
        text = messages.FOND_CREATE_NAME.format(mention)
        keyboard = tg_schemas.ForceReplySchema(
            input_field_placeholder=messages.FOND_CREATE_NAME_PLACEHOLDER)
        task = await self.send_message(text, keyboard)
        await self.wait_task_result(task, MessageHandlerEnum.FOND_CREATE_NAME,
                                    response_to_state={'message_id'})


@handler(MessageHandlerEnum.FOND_CREATE_NAME)
class FondCreateNameHandler(MessageHandler):
    """Fond create name handler."""

    async def handle(self) -> None:
        """Process fond create name."""
        await super().handle()
        await self.delete_income_messages(delete_reply_to_msg=True)
        new_name = self.update.text
        chat = self.chat
        if [b for b in chat.fonds if b.name.lower() == new_name.lower()]:
            mention = self.editor.get_mention(self.user.username)
            text = messages.FOND_CREATE_EXISTS_ERROR.format(new_name, mention)
            keyboard = tg_schemas.ForceReplySchema(
                input_field_placeholder=messages.FOND_CREATE_NAME_PLACEHOLDER)
            task = await self.send_message(text, keyboard)
            await self.wait_task_result(task, MessageHandlerEnum.FOND_CREATE_NAME,
                                        response_to_state={'message_id'})
        else:
            keyboard = self.editor.get_valute_keyboard(chat.valutes)
            text = messages.FOND_CREATE_VALUTE
            task = await self.send_message(text, keyboard)
            await self.wait_task_result(task, CallbackHandlerEnum.FOND_CREATE_VALUTE,
                                        state_data={'fond_name': new_name},
                                        response_to_state={'message_id'})


@handler(CallbackHandlerEnum.FOND_CREATE_VALUTE)
class FondCreateValuteHandler(CallbackHandler, FondCreateMixin):
    """Fond create valute handler."""

    async def handle(self) -> None:
        """Process fond create valute."""
        await super().handle()
        repo = self.db.chat_fond_repo
        await self.delete_income_messages()
        valute: Valute = await self.db.valute_repo.get_by_code(self.update.data)
        fond_name = self.get_state_fond_name()
        fond = ChatFond(name=fond_name, chat_id=self.chat.id, valute_id=valute.id)
        await repo.create_item(fond)
        fond_info = f'{fond_name} | {fond.amount_str} {valute.code}'
        text = '\n\n'.join([
            messages.FOND_INFO.format(fond_info=fond_info),
            messages.FOND_CREATED,
        ])
        keyboard = self.editor.get_hide_keyboard()
        task = await self.send_message(text, keyboard)
        await self.wait_task_result(task, MessageHandlerEnum.DEFAULT)


@handler(CommandHadlerEnum.FOND_LIST)
class FondListHandler(CommandHandler):
    """Fond list handler."""

    async def handle(self) -> None:
        """Process fond list command click."""
        await self.delete_income_messages()
        chat = self.chat
        fonds: list[ChatFond] = chat.fonds
        if not fonds:
            text = messages.FOND_LIST_NO_FONDS
            keyboard = self.editor.get_hide_keyboard()
            await self.send_message(text, keyboard)
            await self.set_state(MessageHandlerEnum.DEFAULT, {})
        else:
            max_name = max(len(f.name) for f in fonds)
            amounts = [f.amount_str for f in fonds]
            max_amount = max(len(a) for a in amounts)
            lines = [f'`{f.get_info(max_name, max_amount)}`' for f in fonds]
            text = messages.FOND_LIST.format('\n'.join(lines))
            keyboard = self.editor.get_hide_keyboard()
            task = await self.send_message(text, keyboard)
            await self.wait_task_result(task, MessageHandlerEnum.DEFAULT)


@handler(CommandHadlerEnum.FOND_SET)
class FondSetHandler(CommandHandler):
    """Fond set amount handler."""

    async def handle(self) -> None:
        """Process fond set amount."""
        await self.delete_income_messages()
        text = messages.FOND_SET_CHOOSE_ONE
        keyboard = self.editor.create_inline_keyboard(
            buttons=[(f.name, f.name) for f in self.chat.fonds],
            add_hide_button=True)
        task = await self.send_message(text, keyboard)
        await self.wait_task_result(task, CallbackHandlerEnum.FOND_SET_CHOOSE_ONE,
                                    response_to_state={'message_id'})


@handler(CallbackHandlerEnum.FOND_SET_CHOOSE_ONE)
class FondSetChooseOneHandler(CallbackHandler, FondCreateMixin):
    """Fond set choose one handler."""

    async def handle(self) -> None:
        """Process picked fond."""
        await super().handle()
        picked_name = self.update.data
        fond = self.get_picked_fond(picked_name)
        original_message_id = self.update.message.message_id
        text = messages.FOND_SET_ENTER_AMOUNT_MAIN.format(fond_name=fond.info)
        await self.edit_message(original_message_id, text)
        text = messages.FOND_SET_ENTER_AMOUNT_REPLY.format(mention=self.user_mention)
        keyboard = tg_schemas.ForceReplySchema(
            input_field_placeholder=messages.FOND_SET_ENTER_AMOUNT_PLACEHOLDER)
        task = await self.send_message(text, keyboard)
        await self.wait_task_result(task, MessageHandlerEnum.FOND_SET_SAVE_AMOUNT,
                                    state_data={'main_message_id': original_message_id,
                                                'fond_name': fond.name},
                                    response_to_state={'message_id'})


@handler(MessageHandlerEnum.FOND_SET_SAVE_AMOUNT)
class FondSetSaveAmountHandler(MessageHandler, FondCreateMixin):
    """Fond set save amount handler."""

    async def handle(self) -> None:
        """Process fond set save amount."""
        await super().handle()
        await self.delete_income_messages(delete_reply_to_msg=True)
        entered_amount = self.update.text
        fond = self.get_picked_fond()
        original_message_id = self.state.data.main_message_id
        try:
            amount = float(entered_amount)
        except ValueError:
            text = messages.FOND_SET_ENTER_AMOUNT_ERROR.format(
                mention=self.user_mention, entered_amount=entered_amount)
            keyboard = tg_schemas.ForceReplySchema(
                input_field_placeholder=messages.FOND_SET_ENTER_AMOUNT_PLACEHOLDER)
            task = await self.send_message(text, reply_markup=keyboard)
            await self.wait_task_result(task, MessageHandlerEnum.FOND_SET_SAVE_AMOUNT,
                                        state_data={'main_message_id': original_message_id,
                                                    'fond_name': fond.name},
                                        response_to_state={'message_id'})
        else:
            repo = self.db.chat_fond_repo
            fond.amount = amount
            fond.updated_at = utils.utcnow()
            fond: ChatFond = await repo.update_item(fond)
            text = '\n\n'.join([
                messages.FOND_INFO.format(fond_info=fond.info),
                messages.FOND_SET_SAVED])
            keyboard = self.editor.get_hide_keyboard()
            task = await self.edit_message(original_message_id, text, keyboard)
            await self.wait_task_result(task, MessageHandlerEnum.DEFAULT)


@handler(CommandHadlerEnum.FOND_DELETE)
class FondDeleteHandler(CommandHandler):
    """Fond delete handler."""

    async def handle(self) -> None:
        """Process fond delete command click."""
        await self.delete_income_messages()
        text = messages.FOND_DELETE_CHOOSE_ONE
        keyboard = self.editor.create_inline_keyboard(
            buttons=[(f.name, f.name) for f in self.chat.fonds],
            add_hide_button=True)
        task = await self.send_message(text, keyboard)
        await self.wait_task_result(task, CallbackHandlerEnum.FOND_DELETE_CHOOSE_ONE,
                                    response_to_state={'message_id'})


@handler(CallbackHandlerEnum.FOND_DELETE_CHOOSE_ONE)
class FondDeleteChooseOneHandler(CallbackHandler, FondCreateMixin):
    """Fond delete choose one handler."""

    async def handle(self) -> None:
        """Process picked fond."""
        await super().handle()
        picked_name = self.update.data
        fond = self.get_picked_fond(picked_name)
        original_message_id = self.update.message.message_id
        text = '\n\n'.join([
            messages.FOND_INFO.format(fond_info=fond.info),
            messages.FOND_DELETE_APPROVE,
        ])
        keyboard = self.editor.get_yes_no_keyboard()
        task = await self.edit_message(original_message_id, text, keyboard)
        await self.wait_task_result(task, CallbackHandlerEnum.FOND_DELETE_CONFIRM,
                                    state_data={'message_id': original_message_id,
                                                'fond_name': fond.name})


@handler(CallbackHandlerEnum.FOND_DELETE_CONFIRM)
class FondDeleteConfirmHandler(CallbackHandler, FondCreateMixin):
    """Fond delete confirm handler."""

    async def handle(self) -> None:
        """Process fond delete confirm."""
        await super().handle()
        fond = self.get_picked_fond()
        decision = bool(int(self.update.data))
        if decision is True:
            repo = self.db.chat_fond_repo
            await repo.delete_item(fond)
            text = '\n\n'.join([
                messages.FOND_INFO.format(fond_info=fond.info),
                messages.FOND_DELETED,
            ])
            keyboard = self.editor.get_hide_keyboard()
            task = await self.edit_message(self.state.data.message_id, text, keyboard)
            await self.wait_task_result(task, MessageHandlerEnum.DEFAULT)
        else:
            await self.delete_income_messages()
            await self.set_state(MessageHandlerEnum.DEFAULT, {})
