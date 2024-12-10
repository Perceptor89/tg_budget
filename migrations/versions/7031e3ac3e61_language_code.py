"""language_code

Revision ID: 7031e3ac3e61
Revises: 80d73005beaa
Create Date: 2024-12-09 21:20:24.078264

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7031e3ac3e61'
down_revision: Union[str, None] = '80d73005beaa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'tg_users',
        'language_code',
        existing_type=sa.VARCHAR(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'tg_users',
        'language_code',
        existing_type=sa.VARCHAR(),
        nullable=False,
    )
