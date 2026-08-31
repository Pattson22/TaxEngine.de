"""
Orchestrates one filing's ELSTER submission: build XML -> ERiC validate ->
ERiC submit -> persist the Transferticket/status back onto the filing.

Mirrors `app/services/tax_calculation_service.py`'s role for the
calculation pipeline — this is the one place DB rows and the
XML/ERiC-client layer meet, so `xml_builder.py` and `client.py` stay
free of DB/session concerns.
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
from app.models.enums import FilingStatus
from app.models.rental_property_statement import RentalPropertyStatement
from app.models.self_employment_statement import SelfEmploymentStatement
from app.models.tax_filing import TaxFiling
from app.models.user import User
from app.models.wage_tax_certificate import WageTaxCertificate


class SubmissionError(ValueError):
    """A filing can't be submitted -- wrong status, missing required data
    (e.g. no Steuer-ID on file), or an ERiC validation/submission failure."""


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
            actual ERiC library (see docs/ELSTER_ERIC_INTEGRATION.md) but
            isn't wired in as this default -- ERiC must never load inside
            the FastAPI web process.

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
    xml = build_est_xml(
        user,
        filing,
        wage_certs,
        capital_income_statements,
        rental_property_statements,
        self_employment_statements,
        children,
        deductions,
        hersteller_id=settings.eric_hersteller_id,
    )

    # "ESt_<Jahr>" is the real ERiC datenartVersion for an income tax
    # return, confirmed against the SDK's own Datenartversionmatrix.ods
    # (also matches the per-year plugin naming, e.g. checkESt_2024.dll).
    datenart_version = f"ESt_{filing.tax_year}"

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
