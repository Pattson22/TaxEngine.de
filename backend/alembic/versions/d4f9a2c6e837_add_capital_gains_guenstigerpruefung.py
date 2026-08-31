"""add capital gains guenstigerpruefung field

Revision ID: d4f9a2c6e837
Revises: b3d6f018c752
Create Date: 2026-09-01 00:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4f9a2c6e837'
down_revision: Union[str, Sequence[str], None] = 'b3d6f018c752'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'tax_filings',
        sa.Column('capital_gains_progressive_election_applied', sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tax_filings', 'capital_gains_progressive_election_applied')
