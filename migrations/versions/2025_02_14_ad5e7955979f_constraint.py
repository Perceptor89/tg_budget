"""constraint

Revision ID: ad5e7955979f
Revises: 3d3b52c1fbe7
Create Date: 2024-11-17 22:30:11.209697

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'ad5e7955979f'
down_revision: Union[str, None] = '3d3b52c1fbe7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        'uq_chat_budget_category_budget_chat',
        'chat_budget_items',
        ['category_id', 'budget_item_id', 'chat_id'])


def downgrade() -> None:
    op.drop_constraint('uq_chat_budget_category_budget_chat', 'chat_budget_items', type_='unique')
