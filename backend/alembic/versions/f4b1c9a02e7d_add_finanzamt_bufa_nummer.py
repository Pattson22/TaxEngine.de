"""add finanzamt bufa nummer

Revision ID: f4b1c9a02e7d
Revises: d2d49df071e7
Create Date: 2026-08-31 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4b1c9a02e7d'
down_revision: Union[str, Sequence[str], None] = 'd2d49df071e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('finanzamt_bufa_nummer', sa.Text(), nullable=True))
    op.create_check_constraint(
        'chk_users_bufa_nummer_format',
        'users',
        "finanzamt_bufa_nummer IS NULL OR finanzamt_bufa_nummer ~ '^\\d{4}$'",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('chk_users_bufa_nummer_format', 'users', type_='check')
    op.drop_column('users', 'finanzamt_bufa_nummer')
