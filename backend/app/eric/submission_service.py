"""
Orchestrates one filing's ELSTER submission: build XML -> ERiC validate ->
ERiC submit -> persist the Transferticket/status back onto the filing.

Mirrors `app/services/tax_calculation_service.py`'s role for the
calculation pipeline — this is the one place DB rows and the
XML/ERiC-client layer meet, so `xml_builder.py` and `client.py` stay
free of DB/session concerns.

Two entry points, both real, deliberately NOT interchangeable:
- `enqueue_submission()` -- inserts an `EricSubmissionJob` row for the
  `eric-submitter` worker process (`app/eric_submitter/worker.py`) to
  claim and process with the real `NativeEricClient`. This is what
  `POST /tax-filings/{id}/submit` calls -- see that route's docstring.
- `submit_filing()` -- synchronous, StubEricClient-backed by default.
  No route calls this; it stays as a directly-testable, dependency-
  injectable entry point (see tests/test_eric.py) and as a template for
  any future synchronous/ops-tooling use.

`build_submission_xml()` is shared by both, so they can never silently
diverge on what XML actually gets built for a given filing.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.eric.client import EricClient, EricSubmissionError, EricValidationError, StubEricClient
from app.eric.xml_builder import build_est_xml
from app.models.capital_income_statement import CapitalIncomeStatement
from app.models.child import Child
from app.models.deduction import Deduction
from app.models.enums import EricSubmissionJobStatus, FilingStatus
from app.models.eric_submission_job import EricSubmissionJob
from app.models.rental_property_statement import RentalPropertyStatement
from app.models.self_employment_statement import SelfEmploymentStatement
from app.models.tax_filing import TaxFiling
from app.models.user import User
from app.models.wage_tax_certificate import WageTaxCertificate


class SubmissionError(ValueError):
    """A filing can't be submitted -- wrong status, missing required data
    (e.g. no Steuer-ID on file), or an ERiC validation/submission failure."""


def datenart_version_for(filing: TaxFiling) -> str:
    """"ESt_<Jahr>" is the real ERiC datenartVersion for an income tax
    return, confirmed against the SDK's own Datenartversionmatrix.ods
    (also matches the per-year plugin naming, e.g. checkESt_2024.dll)."""
    return f"ESt_{filing.tax_year}"


def build_submission_xml(
    db: Session,
    user: User,
    filing: TaxFiling,
    *,
    elster_formatted_steuernummer: str | None = None,
) -> str:
    """Load every row `build_est_xml` needs for this user/tax_year and
    build the E10 XML -- the one place this happens, shared by
    `submit_filing`'s synchronous path and the future `eric-submitter`
    worker's async one (`app/eric_submitter/worker.py`), so they can never
    silently diverge on what gets submitted.

    `elster_formatted_steuernummer` is None here by default deliberately:
    computing it needs a real `NativeEricClient.format_steuernummer_for_elster()`
    call, i.e. a loaded ERiC library -- exactly what must never happen
    inside the FastAPI process `submit_filing()` runs in. Only the worker,
    which already holds a live `NativeEricClient`, passes a real value.
    """
    wage_certs = (
        db.query(WageTaxCertificate)
        .filter(WageTaxCertificate.user_id == user.id, WageTaxCertificate.tax_year == filing.tax_year)
        .all()
    )
    capital_income_statements = (
        db.query(CapitalIncomeStatement)
        .filter(
            CapitalIncomeStatement.user_id == user.id,
            CapitalIncomeStatement.tax_year == filing.tax_year,
        )
        .all()
    )
    rental_property_statements = (
        db.query(RentalPropertyStatement)
        .filter(
            RentalPropertyStatement.user_id == user.id,
            RentalPropertyStatement.tax_year == filing.tax_year,
        )
        .all()
    )
    self_employment_statements = (
        db.query(SelfEmploymentStatement)
        .filter(
            SelfEmploymentStatement.user_id == user.id,
            SelfEmploymentStatement.tax_year == filing.tax_year,
        )
        .all()
    )
    children = (
        db.query(Child)
        .filter(Child.user_id == user.id, Child.tax_year == filing.tax_year)
        .all()
    )
    deductions = (
        db.query(Deduction)
        .filter(Deduction.user_id == user.id, Deduction.tax_year == filing.tax_year)
        .all()
    )
    return build_est_xml(
        user,
        filing,
        wage_certs,
        capital_income_statements,
        rental_property_statements,
        self_employment_statements,
        children,
        deductions,
        hersteller_id=settings.eric_hersteller_id,
        finanzamt_bufa_nummer=user.finanzamt_bufa_nummer,
        elster_formatted_steuernummer=elster_formatted_steuernummer,
    )


def enqueue_submission(db: Session, filing: TaxFiling) -> EricSubmissionJob:
    """Inserts a PENDING `eric_submission_jobs` row for the `eric-submitter`
    worker to claim -- see that module's and `EricSubmissionJob`'s
    docstrings for why this runs in a separate process, never inside the
    FastAPI app. Does not itself validate `filing`'s status -- the calling
    route (`tax_filings.submit_tax_filing`) checks FEE_PAID/Steuer-ID for
    fast feedback, and the worker re-checks both itself right before it
    actually submits, since a queued job can sit for a while.

    `is_amendment` is set here, once, from whether a PRIOR job for this
    same filing already SUCCEEDED -- not from `filing.elster_transfer_ticket`
    itself, which `tax_calculation_service.calculate_tax_filing` clears
    back to None as soon as an already-submitted filing gets recalculated
    (see that function's docstring), specifically so a NEW submission
    cycle can start. The job history in `eric_submission_jobs` is the
    permanent record `enqueue_submission` reads instead -- see
    `EricSubmissionJob.is_amendment`'s docstring for why the worker needs
    this decided up front rather than inferred later."""
    had_prior_success = (
        db.query(EricSubmissionJob)
        .filter(
            EricSubmissionJob.tax_filing_id == filing.id,
            EricSubmissionJob.status == EricSubmissionJobStatus.SUCCEEDED,
        )
        .first()
        is not None
    )
    job = EricSubmissionJob(
        tax_filing_id=filing.id,
        status=EricSubmissionJobStatus.PENDING,
        is_amendment=had_prior_success,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def submit_filing(
    db: Session,
    user: User,
    filing: TaxFiling,
    eric_client: EricClient | None = None,
) -> TaxFiling:
    """Submit a filing to ELSTER via the given (or default) EricClient.

    Args:
        db: session to persist the resulting status/Transferticket.
        user: the taxpayer -- must have a Steuer-ID on file.
        filing: must be FEE_PAID (the processing fee gates submission,
            matching the product's business model: submission is the paid
            feature).
        eric_client: defaults to StubEricClient() if not provided -- see
            that class's docstring for why it must never be relied on in
            production. NativeEricClient is real and verified against the
            actual ERiC library (see docs/ELSTER_ERIC_INTEGRATION.md), but
            no route calls submit_filing() at all -- ERiC must never load
            inside the FastAPI web process, which rules out ever passing
            a NativeEricClient here from a request handler.

    Returns:
        The filing, with status advanced to SUBMITTED then ACCEPTED/
        REJECTED and elster_transfer_ticket/elster_submitted_at/
        elster_accepted_at/elster_rejection_reason populated accordingly.

    Raises:
        SubmissionError: if the filing isn't FEE_PAID, the user has no
            Steuer-ID on file, or ERiC rejects the validation/submission.
    """
    if filing.status != FilingStatus.FEE_PAID:
        raise SubmissionError(
            f"Filing must be FEE_PAID before submission (current status: {filing.status.value})."
        )
    if not user.tax_identification_number:
        raise SubmissionError(
            "User has no tax_identification_number (Steuer-ID) on file -- required for ELSTER submission."
        )

    eric_client = eric_client or StubEricClient()
    xml = build_submission_xml(db, user, filing)
    datenart_version = datenart_version_for(filing)

    try:
        eric_client.validate_xml(xml, datenart_version=datenart_version)
        result = eric_client.submit(xml, datenart_version=datenart_version)
    except EricValidationError as exc:
        filing.elster_rejection_reason = f"ERiC validation failed: {exc}"
        db.commit()
        raise SubmissionError(str(exc)) from exc
    except EricSubmissionError as exc:
        filing.elster_rejection_reason = f"ERiC submission failed: {exc}"
        db.commit()
        raise SubmissionError(str(exc)) from exc

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
    return filing
