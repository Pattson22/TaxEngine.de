"""add aussergewoehnliche_belastung deduction category

Revision ID: e5b8d1f6a209
Revises: c7f2a9e4d183
Create Date: 2026-09-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e5b8d1f6a209'
down_revision: Union[str, Sequence[str], None] = 'c7f2a9e4d183'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Postgres requires ADD VALUE to run outside an explicit transaction
    # block pre-12 -- Alembic runs each migration in its own transaction,
    # so autocommit is used here to stay compatible across versions.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE deduction_category_enum ADD VALUE IF NOT EXISTS 'AUSSERGEWOEHNLICHE_BELASTUNG'")


def downgrade() -> None:
    """Downgrade schema.

    Postgres has no DROP VALUE for enum types -- removing a value requires
    rebuilding the type (rename, create new, migrate column, drop old),
    which risks data loss if any row already uses
    AUSSERGEWOEHNLICHE_BELASTUNG. Left as a no-op: the extra enum value
    existing is harmless, and a real downgrade should be a deliberate,
    reviewed operation, not automatic.
    """
    pass
