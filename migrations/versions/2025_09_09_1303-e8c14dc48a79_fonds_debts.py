"""fonds_debts

Revision ID: e8c14dc48a79
Revises: 0870a330369a
Create Date: 2025-09-09 13:03:19.613225

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e8c14dc48a79'
down_revision: Union[str, None] = '0870a330369a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade."""
    op.create_table(
        'chat_debts',
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('amount', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False),
        sa.Column('valute_id', sa.BigInteger(), nullable=False),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False),
        sa.ForeignKeyConstraint(['chat_id'], ['tg_chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['valute_id'], ['valutes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'chat_fonds',
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('amount', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False),
        sa.Column('valute_id', sa.BigInteger(), nullable=False),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False),
        sa.ForeignKeyConstraint(['chat_id'], ['tg_chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['valute_id'], ['valutes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade."""
    op.drop_table('chat_fonds')
    op.drop_table('chat_debts')
