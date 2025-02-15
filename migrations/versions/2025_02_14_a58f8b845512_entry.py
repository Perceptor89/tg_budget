"""entry

Revision ID: a58f8b845512
Revises: 68dccc47b0f9
Create Date: 2024-12-07 16:56:46.265501

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a58f8b845512'
down_revision: Union[str, None] = '68dccc47b0f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'entries',
        sa.Column('chat_budget_item_id', sa.BigInteger(), nullable=False),
        sa.Column('valute_id', sa.BigInteger(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('data_raw', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['chat_budget_item_id'], ['chat_budget_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['valute_id'], ['valutes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.drop_constraint('uq_chat_budget_category_budget_chat', 'chat_budget_items', type_='unique')
    op.create_unique_constraint('uq_chat_budget_category', 'chat_budget_items', ['category_id', 'budget_item_id', 'chat_id'])


def downgrade() -> None:
    op.drop_constraint('uq_chat_budget_category', 'chat_budget_items', type_='unique')
    op.create_unique_constraint('uq_chat_budget_category_budget_chat', 'chat_budget_items', ['category_id', 'budget_item_id', 'chat_id'])
    op.drop_table('entries')
