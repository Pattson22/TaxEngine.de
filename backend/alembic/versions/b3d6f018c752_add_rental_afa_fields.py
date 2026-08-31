"""add rental property afa fields

Revision ID: b3d6f018c752
Revises: 9a3c7e2b4f81
Create Date: 2026-09-01 00:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3d6f018c752'
down_revision: Union[str, Sequence[str], None] = '9a3c7e2b4f81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'rental_property_statements',
        sa.Column('building_acquisition_cost_cents', sa.BigInteger(), nullable=True),
    )
    op.add_column(
        'rental_property_statements',
        sa.Column('building_completion_year', sa.SmallInteger(), nullable=True),
    )
    op.create_check_constraint(
        'chk_rental_property_building_cost_nonneg',
        'rental_property_statements',
        'building_acquisition_cost_cents IS NULL OR building_acquisition_cost_cents >= 0',
    )
    op.create_check_constraint(
        'chk_rental_property_completion_year_range',
        'rental_property_statements',
        'building_completion_year IS NULL OR building_completion_year BETWEEN 1800 AND 2100',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('chk_rental_property_completion_year_range', 'rental_property_statements', type_='check')
    op.drop_constraint('chk_rental_property_building_cost_nonneg', 'rental_property_statements', type_='check')
    op.drop_column('rental_property_statements', 'building_completion_year')
    op.drop_column('rental_property_statements', 'building_acquisition_cost_cents')
