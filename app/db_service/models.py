import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.sql import func


Base = declarative_base()


class _Base(Base):
    __abstract__ = True

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    created_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=func.now())

    def as_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


class TGChat(_Base):
    __tablename__ = 'tg_chats'

    tg_id = sa.Column(sa.BigInteger, nullable=False)
    title = sa.Column(sa.String, nullable=True)
    type = sa.Column(sa.String(30), nullable=False)

    categories: Mapped[list['Category']] = relationship(
        'Category',
        back_populates='chats',
        secondary='chat_budget_items',
    )


class TGMessage(_Base):
    __tablename__ = 'tg_messages'

    message_id = sa.Column(sa.BigInteger, nullable=False, unique=True)
    date = sa.Column(sa.DateTime(timezone=True), nullable=False)
    chat_id = sa.Column(sa.BigInteger, nullable=False)
    data = sa.Column(sa.JSON, nullable=True)


class TGUser(_Base):
    """Telegram users."""
    __tablename__ = 'tg_users'

    tg_id = sa.Column(sa.BigInteger(), nullable=False)
    first_name = sa.Column(sa.String)
    username = sa.Column(sa.String)
    is_bot = sa.Column(sa.Boolean, nullable=False)
    language_code = sa.Column(sa.String, nullable=False)


class Category(_Base):
    __tablename__ = 'categories'

    name = sa.Column(sa.String, nullable=False)

    chats: Mapped[list['TGChat']] = relationship(
        'TGChat',
        back_populates='categories',
        secondary='chat_budget_items',
    )


class BudgetItem(_Base):
    __tablename__ = 'budget_items'

    name = sa.Column(sa.String, nullable=False)
    type = sa.Column(sa.String, nullable=False)


class ChatBudgetItem(_Base):
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
            name='uq_chat_budget_category_budget_chat'
        ),
    )
