from typing import TYPE_CHECKING, Callable, Dict, Type, Union

from .enums import CallbackHandlerEnum, CommandHadlerEnum, CommonCallbackHandlerEnum, MessageHandlerEnum


if TYPE_CHECKING:
    from .handlers.base import BaseHandler


command_handlers: Dict[str, Type['BaseHandler']] = {}
callback_handlers: Dict[str, Type['BaseHandler']] = {}
message_handlers: Dict[str, Type['BaseHandler']] = {}
common_callback_handlers: Dict[str, Type['BaseHandler']] = {}

registry_mapper = {
    CommandHadlerEnum: command_handlers,
    MessageHandlerEnum: message_handlers,
    CallbackHandlerEnum: callback_handlers,
    CommonCallbackHandlerEnum: common_callback_handlers,
}


def handler(
    enum_value: Union[
        CommandHadlerEnum,
        MessageHandlerEnum,
        CallbackHandlerEnum,
        CommonCallbackHandlerEnum,
    ]
) -> Callable[[Type['BaseHandler']], Type['BaseHandler']]:
    """Decorator to register a handler based on the enum type."""
    def decorator(cls: Type['BaseHandler']) -> Type['BaseHandler']:
        registry = registry_mapper.get(type(enum_value))
        if registry is not None:
            registry[enum_value.value] = cls
            return cls
        else:
            raise ValueError(f'Unknown enum type: {type(enum_value)}')
    return decorator
