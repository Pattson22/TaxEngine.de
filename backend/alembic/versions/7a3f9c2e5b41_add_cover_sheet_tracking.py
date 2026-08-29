"""add komprimiert cover sheet tracking

Revision ID: 7a3f9c2e5b41
Revises: 26ed37e281a2
Create Date: 2026-08-29 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7a3f9c2e5b41'
down_revision: Union[str, Sequence[str], None] = '26ed37e281a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

submission_mode_enum = postgresql.ENUM(
    'KOMPRIMIERT', 'AUTHENTIFIZIERT', name='submission_mode_enum'
)


def upgrade() -> None:
    """Upgrade schema."""
    submission_mode_enum.create(op.get_bind())
    op.add_column(
        'tax_filings',
        sa.Column(
            'submission_mode',
            submission_mode_enum,
            nullable=False,
            server_default='KOMPRIMIERT',
        ),
    )
    op.add_column(
        'tax_filings', sa.Column('cover_sheet_generated_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        'tax_filings', sa.Column('cover_sheet_mailed_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tax_filings', 'cover_sheet_mailed_at')
    op.drop_column('tax_filings', 'cover_sheet_generated_at')
    op.drop_column('tax_filings', 'submission_mode')
    submission_mode_enum.drop(op.get_bind())
