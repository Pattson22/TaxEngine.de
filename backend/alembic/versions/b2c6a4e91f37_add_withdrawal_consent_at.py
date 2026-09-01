"""add withdrawal consent at

Revision ID: b2c6a4e91f37
Revises: f1a8c3e97b26
Create Date: 2026-09-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c6a4e91f37'
down_revision: Union[str, Sequence[str], None] = 'f1a8c3e97b26'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('tax_filings', sa.Column('withdrawal_consent_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tax_filings', 'withdrawal_consent_at')
