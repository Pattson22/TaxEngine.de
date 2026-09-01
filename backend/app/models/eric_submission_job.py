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

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Text, text
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
        # re-enqueued, and a SUCCEEDED filing may later be legitimately
        # re-enqueued again as an amendment (is_amendment=True below). The
        # worker's own idempotency check (does elster_transfer_ticket
        # already exist on the filing, AND is this job NOT an amendment?)
        # is what actually prevents an ACCIDENTAL duplicate submission,
        # matching docs/ELSTER_ERIC_INTEGRATION.md section 5's approach.
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

    # Set once, at enqueue time, by submission_service.enqueue_submission()
    # -- True iff the filing already had a Transferticket from a PRIOR
    # successful submission when this job was created, i.e. this is an
    # amended/corrected resubmission rather than the filing's first ever
    # one. Decided at enqueue time (not inferred later from job history)
    # because the worker's idempotency check (see worker.py's
    # _process_job) needs to know, for THIS job specifically, whether an
    # existing Transferticket on the filing means "someone else already
    # succeeded, skip" (is_amendment=False) or "that's the PREVIOUS
    # submission this one is deliberately superseding" (is_amendment=True)
    # -- see docs/ELSTER_ERIC_INTEGRATION.md for why the E10 Datenart
    # itself carries no "corrected declaration" flag (verified against the
    # real E10-2024.xsd schema; unlike USt/E50's real Ber_Erkl/E3000601
    # field, ESt has no such field at all -- amendment is purely this
    # project's own bookkeeping, never transmitted in the XML).
    is_amendment: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    tax_filing: Mapped["TaxFiling"] = relationship()
