"""tg_message

Revision ID: 79c508173937
Revises: 
Create Date: 2024-05-20 03:32:35.010639

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '79c508173937'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'messages',
        sa.Column('message_id', sa.BigInteger(), nullable=False),
        sa.Column('date', sa.TIMESTAMP(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('other_info', sa.JSON(), nullable=True),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('message_id')
    )


def downgrade() -> None:
    op.drop_table('messages')
