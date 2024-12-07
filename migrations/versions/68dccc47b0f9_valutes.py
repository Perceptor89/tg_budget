"""valutes

Revision ID: 68dccc47b0f9
Revises: dc8eda6e2b4f
Create Date: 2024-12-01 23:35:50.956283

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '68dccc47b0f9'
down_revision: Union[str, None] = 'dc8eda6e2b4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'valutes',
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'chat_valutes',
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('valute_id', sa.BigInteger(), nullable=False),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['chat_id'], ['tg_chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['valute_id'], ['valutes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chat_id', 'valute_id', name='uq_chat_valute')
    )


def downgrade() -> None:
    op.drop_table('chat_valutes')
    op.drop_table('valutes')
