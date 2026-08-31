"""add church_tax_paid deduction category

Revision ID: b6e7f3a19c04
Revises: f4b1c9a02e7d
Create Date: 2026-08-31 23:15:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b6e7f3a19c04'
down_revision: Union[str, Sequence[str], None] = 'f4b1c9a02e7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Postgres requires ADD VALUE to run outside an explicit transaction
    # block pre-12 -- Alembic runs each migration in its own transaction,
    # so autocommit is used here to stay compatible across versions.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE deduction_category_enum ADD VALUE IF NOT EXISTS 'CHURCH_TAX_PAID'")


def downgrade() -> None:
    """Downgrade schema.

    Postgres has no DROP VALUE for enum types -- removing a value requires
    rebuilding the type (rename, create new, migrate column, drop old),
    which risks data loss if any row already uses CHURCH_TAX_PAID. Left as
    a no-op: the extra enum value existing is harmless, and a real
    downgrade should be a deliberate, reviewed operation, not automatic.
    """
    pass
