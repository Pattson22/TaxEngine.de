"""add vorsorgeaufwand deduction fields

Revision ID: c7f2a9e4d183
Revises: a1d8e4f36b52
Create Date: 2026-08-31 22:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7f2a9e4d183'
down_revision: Union[str, Sequence[str], None] = 'a1d8e4f36b52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('tax_filings', sa.Column('altersvorsorge_deduction_cents', sa.BigInteger(), nullable=True))
    op.add_column(
        'tax_filings',
        sa.Column('sonstige_vorsorgeaufwendungen_deduction_cents', sa.BigInteger(), nullable=True),
    )
    op.create_check_constraint(
        'chk_filings_altersvorsorge_nonneg',
        'tax_filings',
        'altersvorsorge_deduction_cents IS NULL OR altersvorsorge_deduction_cents >= 0',
    )
    op.create_check_constraint(
        'chk_filings_sonstige_vorsorge_nonneg',
        'tax_filings',
        'sonstige_vorsorgeaufwendungen_deduction_cents IS NULL '
        'OR sonstige_vorsorgeaufwendungen_deduction_cents >= 0',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('chk_filings_sonstige_vorsorge_nonneg', 'tax_filings', type_='check')
    op.drop_constraint('chk_filings_altersvorsorge_nonneg', 'tax_filings', type_='check')
    op.drop_column('tax_filings', 'sonstige_vorsorgeaufwendungen_deduction_cents')
    op.drop_column('tax_filings', 'altersvorsorge_deduction_cents')
