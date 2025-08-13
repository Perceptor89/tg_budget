"""balances

Revision ID: 0870a330369a
Revises: cfc3de425b5e
Create Date: 2025-07-14 18:19:38.344197

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0870a330369a'
down_revision: Union[str, None] = 'cfc3de425b5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade."""
    op.create_table(
        'chat_balances',
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('amount', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('valute_id', sa.BigInteger(), nullable=False),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['chat_id'], ['tg_chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['valute_id'], ['valutes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.alter_column('tg_user_states', 'state', new_column_name='name')


def downgrade() -> None:
    """Downgrade."""
    op.alter_column('tg_user_states', 'name', new_column_name='state')
    op.drop_table('chat_balances')
