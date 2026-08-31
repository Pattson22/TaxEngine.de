"""add aussergewoehnliche belastungen deduction field

Revision ID: 9a3c7e2b4f81
Revises: e5b8d1f6a209
Create Date: 2026-09-01 00:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a3c7e2b4f81'
down_revision: Union[str, Sequence[str], None] = 'e5b8d1f6a209'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'tax_filings', sa.Column('aussergewoehnliche_belastungen_deduction_cents', sa.BigInteger(), nullable=True)
    )
    op.create_check_constraint(
        'chk_filings_aussergewoehnliche_belastungen_nonneg',
        'tax_filings',
        'aussergewoehnliche_belastungen_deduction_cents IS NULL '
        'OR aussergewoehnliche_belastungen_deduction_cents >= 0',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('chk_filings_aussergewoehnliche_belastungen_nonneg', 'tax_filings', type_='check')
    op.drop_column('tax_filings', 'aussergewoehnliche_belastungen_deduction_cents')
