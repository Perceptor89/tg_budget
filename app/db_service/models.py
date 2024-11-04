import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func


Base = declarative_base()


class _Base(Base):
    __abstract__ = True

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    created_at = sa.Column(sa.DateTime, nullable=False, server_default=func.now())

    def as_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


class TGMessage(_Base):
    __tablename__ = 'messages'

    message_id = sa.Column(sa.BigInteger, nullable=False, unique=True)
    date = sa.Column(sa.TIMESTAMP, nullable=False)
    chat_id = sa.Column(sa.BigInteger, nullable=False)
    other_info = sa.Column(sa.JSON, nullable=True)


class TGUser(_Base):
    """Telegram users."""
    __tablename__ = 'tg_users'

    tg_id = sa.Column(sa.BigInteger(), nullable=False)
    first_name = sa.Column(sa.String)
    username = sa.Column(sa.String)
