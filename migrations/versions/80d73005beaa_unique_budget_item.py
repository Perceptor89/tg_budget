"""unique_budget_item

Revision ID: 80d73005beaa
Revises: a58f8b845512
Create Date: 2024-12-08 11:00:04.864374

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '80d73005beaa'
down_revision: Union[str, None] = 'a58f8b845512'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint('uq_budget_item', 'budget_items', ['name', 'type'])


def downgrade() -> None:
    op.drop_constraint('uq_budget_item', 'budget_items', type_='unique')
