"""user_state

Revision ID: dc8eda6e2b4f
Revises: ad5e7955979f
Create Date: 2024-11-19 16:52:22.559487

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'dc8eda6e2b4f'
down_revision: Union[str, None] = 'ad5e7955979f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('tg_user_states',
    sa.Column('tg_user_id', sa.BigInteger(), nullable=False),
    sa.Column('state', sa.String(), nullable=False),
    sa.Column('data_raw', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['tg_user_id'], ['tg_users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('tg_user_states')
