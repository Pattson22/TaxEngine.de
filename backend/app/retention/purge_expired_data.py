"""Automated purge of tax data past its retention window (see
app/config.py's `data_retention_years` docstring for the legal basis and
the caveat that the exact figure still needs a lawyer's confirmation --
same status as the legal pages themselves, see
frontend/src/components/legal.tsx's LegalDraftNotice).

Entry point: `python -m app.retention.purge_expired_data` -- meant to run
on a schedule (e.g. a dedicated Railway service with a cron schedule),
not inside the request/response cycle of the main FastAPI app, same
process-isolation reasoning as the eric-submitter worker (see
docs/ELSTER_ERIC_INTEGRATION.md section 2).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.config import settings
from app.documents.storage import DocumentStorage, S3DocumentStorage
from app.models.capital_income_statement import CapitalIncomeStatement
from app.models.child import Child
from app.models.deduction import Deduction
from app.models.rental_property_statement import RentalPropertyStatement
from app.models.self_employment_statement import SelfEmploymentStatement
from app.models.tax_filing import TaxFiling
from app.models.wage_tax_certificate import WageTaxCertificate

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PurgeResult:
    cutoff_tax_year: int
    wage_tax_certificates_deleted: int
    capital_income_statements_deleted: int
    rental_property_statements_deleted: int
    self_employment_statements_deleted: int
    children_deleted: int
    deductions_deleted: int
    tax_filings_deleted: int


def _cutoff_tax_year(retention_years: int, as_of: date) -> int:
    """The most recent tax_year now eligible for deletion. Measured from
    the END of the tax year, not its start: a tax_year=Y return covers
    income through Y-12-31, so `retention_years` full calendar years must
    have elapsed AFTER that date before it's eligible -- e.g. with
    retention_years=10 and as_of=2026-01-01, tax_year 2015 is the newest
    eligible year (2015-12-31 plus 10 full years is 2025-12-31, already
    past)."""
    return as_of.year - retention_years - 1


def purge_expired_tax_years(
    db: Session,
    storage: DocumentStorage,
    *,
    retention_years: int | None = None,
    as_of: date | None = None,
) -> PurgeResult:
    """Deletes every tax-year record (income/deduction tables and the
    filing itself) older than the retention window, across all users --
    this is a global age cutoff, not a per-user one.

    Each WageTaxCertificate's underlying uploaded file is deleted from
    object storage BEFORE its database row, so a crash mid-run can at
    worst leave an orphaned DB row (caught by the next run, since the
    file deletion is what's missing) rather than an orphaned file with no
    record it ever existed.

    Deliberately does NOT check FilingStatus -- a filing still sitting in
    DRAFT or otherwise unresolved after `retention_years` is itself a
    decade-old edge case this module does not try to special-case; see
    this module's docstring for the broader legal caveat.
    """
    cutoff = _cutoff_tax_year(retention_years or settings.data_retention_years, as_of or date.today())

    certificates = db.query(WageTaxCertificate).filter(WageTaxCertificate.tax_year <= cutoff).all()
    for certificate in certificates:
        if certificate.source_document_url:
            storage.delete(certificate.source_document_url)
        db.delete(certificate)
    wage_tax_certificates_deleted = len(certificates)

    def _bulk_delete(model: type) -> int:
        return db.query(model).filter(model.tax_year <= cutoff).delete(synchronize_session=False)

    capital_income_statements_deleted = _bulk_delete(CapitalIncomeStatement)
    rental_property_statements_deleted = _bulk_delete(RentalPropertyStatement)
    self_employment_statements_deleted = _bulk_delete(SelfEmploymentStatement)
    children_deleted = _bulk_delete(Child)
    deductions_deleted = _bulk_delete(Deduction)
    # Last: EricSubmissionJob rows for a purged filing cascade
    # automatically via their tax_filing_id FK's ondelete="CASCADE" (see
    # models/eric_submission_job.py) -- no separate delete needed here.
    tax_filings_deleted = _bulk_delete(TaxFiling)

    db.commit()

    result = PurgeResult(
        cutoff_tax_year=cutoff,
        wage_tax_certificates_deleted=wage_tax_certificates_deleted,
        capital_income_statements_deleted=capital_income_statements_deleted,
        rental_property_statements_deleted=rental_property_statements_deleted,
        self_employment_statements_deleted=self_employment_statements_deleted,
        children_deleted=children_deleted,
        deductions_deleted=deductions_deleted,
        tax_filings_deleted=tax_filings_deleted,
    )
    logger.info("Retention purge complete: %s", result)
    return result


if __name__ == "__main__":
    from app.database import SessionLocal

    logging.basicConfig(level=logging.INFO)
    session = SessionLocal()
    try:
        purge_expired_tax_years(session, S3DocumentStorage())
    finally:
        session.close()
