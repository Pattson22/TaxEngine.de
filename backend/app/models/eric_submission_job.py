"""SQLAlchemy model for `eric_submission_jobs` — the queue the
`eric-submitter` worker process polls (see app/eric_submitter/worker.py).

Postgres-backed rather than Redis/SQS: no new infra dependency, and
docs/ELSTER_ERIC_INTEGRATION.md section 2 explicitly names this as an
acceptable choice ("e.g. a Postgres-backed job table or Redis/SQS").
`SELECT ... FOR UPDATE SKIP LOCKED` (see the worker's claim query) is what
makes this safe for multiple worker instances to poll concurrently without
double-processing a row.

A row here is created by `submission_service.enqueue_submission()`, which
`POST /tax-filings/{id}/submit` calls -- see that route's docstring for
the full async flow (enqueue -> worker claims/processes -> frontend polls
GET /{id}/submission-job for the outcome).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import EricSubmissionJobStatus, pg_enum

if TYPE_CHECKING:
    from app.models.tax_filing import TaxFiling


class EricSubmissionJob(Base):
    __tablename__ = "eric_submission_jobs"
    __table_args__ = (
        # Not UNIQUE on tax_filing_id -- a failed job's filing may be
        # re-enqueued, and the worker's own idempotency check (does
        # elster_transfer_ticket already exist on the filing?) is what
        # actually prevents a duplicate real submission, matching
        # docs/ELSTER_ERIC_INTEGRATION.md section 5's documented approach.
        Index("idx_eric_submission_jobs_status", "status"),
        Index("idx_eric_submission_jobs_tax_filing_id", "tax_filing_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tax_filing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tax_filings.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[EricSubmissionJobStatus] = mapped_column(
        pg_enum(EricSubmissionJobStatus, "eric_submission_job_status_enum"),
        nullable=False,
        default=EricSubmissionJobStatus.PENDING,
        server_default="PENDING",
    )

    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    transfer_ticket: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    tax_filing: Mapped["TaxFiling"] = relationship()
