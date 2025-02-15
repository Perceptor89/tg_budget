from functools import cached_property
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql import func, text

from app.db_service.schemas import StateDataSchema


Base = declarative_base()


class _Base(Base):
    __abstract__ = True

    def as_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


class _BaseExtended(_Base):
    __abstract__ = True

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=func.now())


class ChatBudgetItem(_BaseExtended):
    __tablename__ = 'chat_budget_items'

    category_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey('categories.id', ondelete='SET NULL'),
        nullable=False,
    )
    budget_item_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey('budget_items.id', ondelete='SET NULL'),
        nullable=True,
    )
    chat_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey('tg_chats.id', ondelete='CASCADE'),
        nullable=False,
    )

    __table_args__ = (
        sa.UniqueConstraint(
            'category_id', 'budget_item_id', 'chat_id',
            name='uq_chat_budget_category'
        ),
    )


class TGChat(_BaseExtended):
    __tablename__ = 'tg_chats'

    tg_id = sa.Column(sa.BigInteger, nullable=False)
    title = sa.Column(sa.String, nullable=True)
    type = sa.Column(sa.String(30), nullable=False)

    categories: Mapped[list['Category']] = relationship(
        'Category',
        back_populates='chats',
        secondary='chat_budget_items',
    )
    valutes: Mapped[list['Valute']] = relationship(
        'Valute',
        back_populates='chats',
        secondary='chat_valutes',
    )


class TGMessage(_BaseExtended):
    __tablename__ = 'tg_messages'

    message_id = sa.Column(sa.BigInteger, nullable=False, unique=True)
    date = sa.Column(sa.DateTime(timezone=True), nullable=False)
    chat_id = sa.Column(sa.BigInteger, nullable=False)
    data = sa.Column(sa.JSON, nullable=True)


class TGUser(_BaseExtended):
    """Telegram users."""
    __tablename__ = 'tg_users'

    tg_id = sa.Column(sa.BigInteger(), nullable=False)
    first_name = sa.Column(sa.String)
    username = sa.Column(sa.String)
    is_bot = sa.Column(sa.Boolean, nullable=False)
    language_code = sa.Column(sa.String)


class Category(_BaseExtended):
    __tablename__ = 'categories'

    name = sa.Column(sa.String, nullable=False)

    chats: Mapped[list['TGChat']] = relationship(
        'TGChat',
        back_populates='categories',
        secondary='chat_budget_items',
    )
    budget_items: Mapped[list['BudgetItem']] = relationship(
        'BudgetItem',
        back_populates='categories',
        secondary='chat_budget_items',
        overlaps='categories,chats',
    )


class BudgetItem(_BaseExtended):
    __tablename__ = 'budget_items'

    name = sa.Column(sa.String, nullable=False)
    type = sa.Column(sa.String, nullable=False)

    categories: Mapped[list['Category']] = relationship(
        'Category',
        back_populates='budget_items',
        secondary='chat_budget_items',
        overlaps='categories,chats',
    )

    __table_args__ = (
        sa.UniqueConstraint('name', 'type', name='uq_budget_item'),
    )


class TGUserState(_BaseExtended):
    __tablename__ = 'tg_user_states'

    tg_user_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey('tg_users.id', ondelete='CASCADE'),
        nullable=False,
    )
    state = sa.Column(sa.String, nullable=False)
    data_raw = sa.Column(JSONB, nullable=False, default=dict())

    @cached_property
    def data(self) -> StateDataSchema:
        return StateDataSchema.model_validate(self.data_raw)


class Valute(_BaseExtended):
    __tablename__ = 'valutes'

    name = sa.Column(sa.String, nullable=False)
    symbol = sa.Column(sa.String, nullable=False)
    code = sa.Column(sa.String, nullable=False)

    chats: Mapped[list['TGChat']] = relationship(
        'TGChat',
        back_populates='valutes',
        secondary='chat_valutes',
    )


class ChatValute(_BaseExtended):
    __tablename__ = 'chat_valutes'

    chat_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey('tg_chats.id', ondelete='CASCADE'),
        nullable=False,
    )
    valute_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey('valutes.id', ondelete='CASCADE'),
        nullable=False,
    )

    __table_args__ = (
        sa.UniqueConstraint('chat_id', 'valute_id', name='uq_chat_valute'),
    )


class Entry(_BaseExtended):
    __tablename__ = 'entries'

    chat_budget_item_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey('chat_budget_items.id', ondelete='CASCADE'),
        nullable=False,
    )
    valute_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey('valutes.id', ondelete='CASCADE'),
        nullable=False,
    )
    amount = sa.Column(sa.Float, nullable=False)
    data_raw = sa.Column(JSONB, nullable=False, default=dict())


class ValuteRate(_Base):
    __tablename__ = 'valute_rates'

    valute_from_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey('valutes.id', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
    )
    valute_to_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey('valutes.id', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
    )
    rate = sa.Column(sa.Float, nullable=False)
    date = sa.Column(sa.Date, nullable=False, server_default=text('CURRENT_DATE'), primary_key=True)


class ValuteExchange(_BaseExtended):
    __tablename__ = 'valute_exchanges'

    chat_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey('tg_chats.id', ondelete='CASCADE'),
        nullable=False,
    )
    valute_from_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey('valutes.id', ondelete='CASCADE'),
        nullable=False,
    )
    valute_to_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey('valutes.id', ondelete='CASCADE'),
        nullable=False,
    )
    valute_from_amount = sa.Column(sa.Float, nullable=False)
    valute_to_amount = sa.Column(sa.Float, nullable=False)
