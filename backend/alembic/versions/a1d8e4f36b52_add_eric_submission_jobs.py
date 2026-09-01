"""add eric submission jobs

Revision ID: a1d8e4f36b52
Revises: b6e7f3a19c04
Create Date: 2026-08-31 23:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1d8e4f36b52'
down_revision: Union[str, Sequence[str], None] = 'b6e7f3a19c04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# create_type=False -- see the identical comment in
# d2d49df071e7_add_children.py; the same double-create-on-CREATE-TABLE
# failure applies here.
eric_submission_job_status_enum = postgresql.ENUM(
    'PENDING', 'PROCESSING', 'SUCCEEDED', 'FAILED', name='eric_submission_job_status_enum',
    create_type=False,
)


def upgrade() -> None:
    """Upgrade schema."""
    eric_submission_job_status_enum.create(op.get_bind())
    op.create_table('eric_submission_jobs',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('tax_filing_id', sa.UUID(), nullable=False),
    sa.Column('status', eric_submission_job_status_enum, server_default='PENDING', nullable=False),
    sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('transfer_ticket', sa.Text(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['tax_filing_id'], ['tax_filings.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_eric_submission_jobs_status', 'eric_submission_jobs', ['status'], unique=False)
    op.create_index(
        'idx_eric_submission_jobs_tax_filing_id', 'eric_submission_jobs', ['tax_filing_id'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_eric_submission_jobs_tax_filing_id', table_name='eric_submission_jobs')
    op.drop_index('idx_eric_submission_jobs_status', table_name='eric_submission_jobs')
    op.drop_table('eric_submission_jobs')
    eric_submission_job_status_enum.drop(op.get_bind())
