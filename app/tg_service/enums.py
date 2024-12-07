import enum


class TGChatTypeEnum(str, enum.Enum):

    PRIVATE = 'private'
    GROUP = 'group'
    SUPERGROUP = 'supergroup'


class TGEntityTypeEnum(str, enum.Enum):

    BOT_COMMAND = 'bot_command'
    MENTION = 'mention'
