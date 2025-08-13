import enum


class TGChatTypeEnum(str, enum.Enum):
    """Telegram chat types."""

    PRIVATE = 'private'
    GROUP = 'group'
    SUPERGROUP = 'supergroup'


class TGEntityTypeEnum(str, enum.Enum):
    """Telegram message entity types."""

    BOT_COMMAND = 'bot_command'
    MENTION = 'mention'
    CODE = 'code'
