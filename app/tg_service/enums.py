import enum


class TGChatTypeEnum(str, enum.Enum):

    PRIVATE = 'private'
    GROUP = 'group'


class TGEntityTypeEnum(str, enum.Enum):

    BOT_COMMAND = 'bot_command'
