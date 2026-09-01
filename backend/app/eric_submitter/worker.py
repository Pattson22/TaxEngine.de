"""
Standalone worker process that polls `eric_submission_jobs` and submits
each one via the real `NativeEricClient`.

Run as its own OS process, SEPARATE from the FastAPI app (uvicorn/gunicorn
worker) -- see docs/ELSTER_ERIC_INTEGRATION.md section 2 for exactly why:
crash isolation (a segfault inside ericapi.dll must only kill this worker,
never an in-flight web request), independent ERiC-version upgrades, and
keeping cffi memory-safety concerns off the request path entirely.

*** REFERENCE IMPLEMENTATION, NOT A PRODUCTION DEPLOYMENT ***
This is a real, working claim/process/persist loop -- not a sketch -- but
it has no supervisor/restart policy, no concurrency beyond one job at a
time, and no graceful-shutdown signal handling. Harden this (or replace
the polling loop with a proper task-queue framework) before running it
against production traffic; what matters here is that the claim query,
the ERiC lifecycle, and the idempotency check are all real and correct.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.eric.client import EricSubmissionError, EricValidationError, NativeEricClient
from app.eric.submission_service import build_submission_xml, datenart_version_for
from app.models.enums import EricSubmissionJobStatus, FilingStatus
from app.models.eric_submission_job import EricSubmissionJob
from app.models.tax_filing import TaxFiling
from app.models.user import User

logger = logging.getLogger(__name__)

_POLL_INTERVAL_SECONDS = 5


def _claim_next_job(db: Session) -> EricSubmissionJob | None:
    """`SELECT ... FOR UPDATE SKIP LOCKED` -- the standard Postgres
    pattern for a job queue multiple worker instances can poll
    concurrently without ever double-claiming the same row (SKIP LOCKED
    makes a row another transaction already holds invisible to this one,
    instead of blocking on it)."""
    job = (
        db.execute(
            select(EricSubmissionJob)
            .where(EricSubmissionJob.status == EricSubmissionJobStatus.PENDING)
            .order_by(EricSubmissionJob.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        .scalars()
        .first()
    )
    if job is None:
        return None
    job.status = EricSubmissionJobStatus.PROCESSING
    job.claimed_at = datetime.now(timezone.utc)
    db.commit()
    return job


def _succeed(db: Session, job: EricSubmissionJob, transfer_ticket: str) -> None:
    job.status = EricSubmissionJobStatus.SUCCEEDED
    job.transfer_ticket = transfer_ticket
    job.completed_at = datetime.now(timezone.utc)
    db.commit()


def _fail(db: Session, job: EricSubmissionJob, message: str) -> None:
    job.status = EricSubmissionJobStatus.FAILED
    job.error_message = message
    job.completed_at = datetime.now(timezone.utc)
    db.commit()


def _process_job(db: Session, eric_client: NativeEricClient, job: EricSubmissionJob) -> None:
    filing = db.get(TaxFiling, job.tax_filing_id)
    if filing is None:
        _fail(db, job, "TaxFiling no longer exists.")
        return
    user = db.get(User, filing.user_id)
    if user is None:
        _fail(db, job, "User no longer exists.")
        return

    # Idempotency: never re-submit a filing that already has a real
    # Transferticket -- see docs/ELSTER_ERIC_INTEGRATION.md section 5.
    # Amendment jobs (job.is_amendment, set at enqueue time -- see
    # submission_service.enqueue_submission) are the deliberate exception:
    # by the time an amendment job is claimed, calculate_tax_filing has
    # already cleared filing.elster_transfer_ticket back to None (a fresh
    # recalculation always precedes a resubmission), so in practice this
    # branch only ever fires for a genuine accidental duplicate -- the
    # is_amendment check is a second, explicit guard against ever treating
    # a real prior success as an accident.
    if filing.elster_transfer_ticket and not job.is_amendment:
        _succeed(db, job, filing.elster_transfer_ticket)
        return

    # Mirrors submit_filing()'s own pre-flight checks exactly -- a job can
    # sit in the queue for a while, so the filing's state must be
    # re-verified at claim time, not trusted from when it was enqueued.
    if filing.status != FilingStatus.FEE_PAID:
        _fail(db, job, f"Filing must be FEE_PAID (current status: {filing.status.value}).")
        return
    if not user.tax_identification_number:
        _fail(db, job, "User has no tax_identification_number (Steuer-ID) on file.")
        return

    elster_stnr: str | None = None
    if user.steuernummer and user.finanzamt_bufa_nummer:
        try:
            elster_stnr = eric_client.format_steuernummer_for_elster(
                user.steuernummer, bundesfinanzamtsnr=user.finanzamt_bufa_nummer
            )
        except (EricValidationError, EricSubmissionError) as exc:
            # Non-fatal: xml_builder.build_est_xml simply omits the
            # Vorsatz block without a converted Steuernummer -- the rest
            # of the filing can still be validated/submitted.
            logger.warning("format_steuernummer_for_elster failed for job %s: %s", job.id, exc)

    xml = build_submission_xml(db, user, filing, elster_formatted_steuernummer=elster_stnr)
    datenart_version = datenart_version_for(filing)

    try:
        eric_client.validate_xml(xml, datenart_version=datenart_version)
        result = eric_client.submit(xml, datenart_version=datenart_version)
    except (EricValidationError, EricSubmissionError) as exc:
        filing.elster_rejection_reason = f"ERiC error: {exc}"
        db.commit()
        _fail(db, job, str(exc))
        return

    now = datetime.now(timezone.utc)
    filing.status = FilingStatus.SUBMITTED
    filing.elster_submitted_at = now
    filing.elster_transfer_ticket = result.transfer_ticket
    if result.accepted:
        filing.status = FilingStatus.ACCEPTED
        filing.elster_accepted_at = now
        filing.elster_rejection_reason = None
    else:
        filing.status = FilingStatus.REJECTED
        filing.elster_rejection_reason = result.rejection_reason
    db.commit()

    _succeed(db, job, result.transfer_ticket)


def run_forever() -> None:
    """Main loop: claim a PENDING job, process it, repeat -- polling every
    `_POLL_INTERVAL_SECONDS` when the queue is empty. Runs until killed
    (Ctrl+C / SIGTERM); `EricBeende()` is guaranteed via `finally` so
    ERiC's own shutdown contract is honored even then."""
    if not settings.eric_sdk_path:
        raise RuntimeError(
            "ERIC_SDK_PATH is not configured -- see app/config.py and "
            "docs/ELSTER_ERIC_INTEGRATION.md."
        )
    eric_client = NativeEricClient(sdk_path=settings.eric_sdk_path)
    logger.info("eric-submitter worker started.")
    try:
        while True:
            db = SessionLocal()
            try:
                job = _claim_next_job(db)
                if job is None:
                    db.close()
                    time.sleep(_POLL_INTERVAL_SECONDS)
                    continue
                logger.info("Processing eric_submission_job %s", job.id)
                _process_job(db, eric_client, job)
            finally:
                db.close()
    finally:
        eric_client.close()
        logger.info("eric-submitter worker stopped.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever()
