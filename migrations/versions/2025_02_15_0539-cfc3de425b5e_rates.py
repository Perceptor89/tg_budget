"""rates

Revision ID: cfc3de425b5e
Revises: 7031e3ac3e61
Create Date: 2025-02-15 05:39:52.971656

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'cfc3de425b5e'
down_revision: Union[str, None] = '7031e3ac3e61'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'valute_exchanges',
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('valute_from_id', sa.BigInteger(), nullable=False),
        sa.Column('valute_to_id', sa.BigInteger(), nullable=False),
        sa.Column('valute_from_amount', sa.Float(), nullable=False),
        sa.Column('valute_to_amount', sa.Float(), nullable=False),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['chat_id'], ['tg_chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['valute_from_id'], ['valutes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['valute_to_id'], ['valutes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'valute_rates',
        sa.Column('valute_from_id', sa.BigInteger(), nullable=False),
        sa.Column('valute_to_id', sa.BigInteger(), nullable=False),
        sa.Column('rate', sa.Float(), nullable=False),
        sa.Column('date', sa.Date(), server_default=sa.text('CURRENT_DATE'), nullable=False),
        sa.ForeignKeyConstraint(['valute_from_id'], ['valutes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['valute_to_id'], ['valutes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('valute_from_id', 'valute_to_id', 'date'),
    )


def downgrade() -> None:
    op.drop_table('valute_rates')
    op.drop_table('valute_exchanges')
