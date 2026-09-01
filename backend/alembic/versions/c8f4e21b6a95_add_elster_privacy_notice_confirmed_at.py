"""add elster privacy notice confirmed at

Revision ID: c8f4e21b6a95
Revises: b2c6a4e91f37
Create Date: 2026-09-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8f4e21b6a95'
down_revision: Union[str, Sequence[str], None] = 'b2c6a4e91f37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('elster_privacy_notice_confirmed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'elster_privacy_notice_confirmed_at')
