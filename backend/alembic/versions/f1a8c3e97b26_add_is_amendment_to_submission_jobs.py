"""add is_amendment to eric_submission_jobs

Revision ID: f1a8c3e97b26
Revises: d4f9a2c6e837
Create Date: 2026-09-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a8c3e97b26'
down_revision: Union[str, Sequence[str], None] = 'd4f9a2c6e837'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'eric_submission_jobs',
        sa.Column('is_amendment', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('eric_submission_jobs', 'is_amendment')
