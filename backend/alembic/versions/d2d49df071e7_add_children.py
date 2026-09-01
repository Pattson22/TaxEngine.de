"""add children

Revision ID: d2d49df071e7
Revises: 7a3f9c2e5b41
Create Date: 2026-08-31 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd2d49df071e7'
down_revision: Union[str, Sequence[str], None] = '7a3f9c2e5b41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# create_type=False -- upgrade() creates the type explicitly below via
# .create(), and without this the CREATE TABLE below would ALSO try to
# auto-create it (op.create_table compiles a real CreateTable DDL
# construct, unlike op.add_column), failing with "type already exists"
# against a genuinely fresh database. Confirmed by reproducing this
# exact failure with a clean docker-compose Postgres.
child_relationship_type_enum = postgresql.ENUM(
    'BIOLOGICAL_OR_ADOPTED', 'FOSTER', 'GRANDCHILD_OR_STEP', name='child_relationship_type_enum',
    create_type=False,
)


def upgrade() -> None:
    """Upgrade schema."""
    child_relationship_type_enum.create(op.get_bind())
    op.create_table('children',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('tax_year', sa.SmallInteger(), nullable=False),
    sa.Column('first_name', sa.Text(), nullable=False),
    sa.Column('last_name', sa.Text(), nullable=True),
    sa.Column('date_of_birth', sa.Date(), nullable=False),
    sa.Column('tax_identification_number', sa.Text(), nullable=True),
    sa.Column('relationship_type', child_relationship_type_enum, server_default='BIOLOGICAL_OR_ADOPTED', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("tax_identification_number IS NULL OR tax_identification_number ~ '^\\d{11}$'", name='chk_children_steuer_id_format'),
    sa.CheckConstraint('tax_year BETWEEN 2015 AND 2100', name='chk_children_tax_year'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_children_user_year', 'children', ['user_id', 'tax_year'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_children_user_year', table_name='children')
    op.drop_table('children')
    child_relationship_type_enum.drop(op.get_bind())
