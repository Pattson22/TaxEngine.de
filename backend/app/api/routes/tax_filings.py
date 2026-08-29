from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.eric.submission_service import SubmissionError, submit_filing
from app.models.tax_filing import TaxFiling
from app.models.user import User
from app.schemas.payment import PaymentIntentResponse
from app.schemas.tax_filing import TaxFilingCreate, TaxFilingRead, TaxFilingUpdate
from app.services.payment_service import PaymentError, create_payment_intent_for_filing
from app.services.tax_calculation_service import TaxCalculationError, calculate_tax_filing

router = APIRouter(prefix="/tax-filings", tags=["tax-filings"])


def _get_owned_filing_or_404(filing_id: uuid.UUID, user: User, db: Session) -> TaxFiling:
    filing = db.get(TaxFiling, filing_id)
    if filing is None or filing.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tax filing not found.")
    return filing


@router.post("", response_model=TaxFilingRead, status_code=status.HTTP_201_CREATED)
def create_tax_filing(
    payload: TaxFilingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaxFiling:
    existing = (
        db.query(TaxFiling)
        .filter(TaxFiling.user_id == current_user.id, TaxFiling.tax_year == payload.tax_year)
        .one_or_none()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A tax filing for {payload.tax_year} already exists.",
        )

    filing = TaxFiling(user_id=current_user.id, tax_year=payload.tax_year)
    db.add(filing)
    db.commit()
    db.refresh(filing)
    return filing


@router.get("", response_model=list[TaxFilingRead])
def list_tax_filings(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[TaxFiling]:
    return (
        db.query(TaxFiling)
        .filter(TaxFiling.user_id == current_user.id)
        .order_by(TaxFiling.tax_year.desc())
        .all()
    )


@router.get("/{filing_id}", response_model=TaxFilingRead)
def get_tax_filing(
    filing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaxFiling:
    return _get_owned_filing_or_404(filing_id, current_user, db)


@router.patch("/{filing_id}", response_model=TaxFilingRead)
def update_tax_filing(
    filing_id: uuid.UUID,
    payload: TaxFilingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaxFiling:
    """Update Günstigerprüfung inputs (number_of_children,
    kindergeld_received_cents) before calculating. Values here take effect
    the next time `/calculate` runs -- they don't retroactively touch
    already-computed figures."""
    filing = _get_owned_filing_or_404(filing_id, current_user, db)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(filing, field, value)

    db.commit()
    db.refresh(filing)
    return filing


@router.post("/{filing_id}/calculate", response_model=TaxFilingRead)
def calculate_filing(
    filing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaxFiling:
    """Run the tax_engine pipeline against this user's wage tax
    certificates + deductions for the filing's tax_year, and persist the
    resulting refund estimate/breakdown onto the filing."""
    filing = _get_owned_filing_or_404(filing_id, current_user, db)

    try:
        filing = calculate_tax_filing(db, current_user, filing.tax_year)
    except TaxCalculationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    db.commit()
    db.refresh(filing)
    return filing


@router.post("/{filing_id}/payment-intent", response_model=PaymentIntentResponse)
def create_filing_payment_intent(
    filing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentIntentResponse:
    """Create a Stripe PaymentIntent for the flat €34.90 processing fee.

    The frontend uses the returned `client_secret` with Stripe.js/Elements
    to collect card details directly against Stripe (never touching this
    backend, keeping it out of PCI scope). The filing only transitions to
    FEE_PAID once Stripe confirms the charge via the `/webhooks/stripe`
    endpoint — creating a payment intent here does not, by itself, mark
    anything as paid.
    """
    filing = _get_owned_filing_or_404(filing_id, current_user, db)

    try:
        intent = create_payment_intent_for_filing(filing)
    except PaymentError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    db.commit()
    return PaymentIntentResponse(
        client_secret=intent.client_secret,
        payment_intent_id=intent.id,
        amount_cents=filing.processing_fee_cents,
    )


@router.post("/{filing_id}/submit", response_model=TaxFilingRead)
def submit_tax_filing(
    filing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaxFiling:
    """Submit a FEE_PAID filing to ELSTER.

    *** Currently uses StubEricClient, not a real ERiC submission ***
    See app/eric/client.py's NativeEricClient docstring: real submission
    requires a signed BZSt developer agreement and the actual ERiC
    library, neither of which exists yet. This endpoint exercises the
    real orchestration (XML generation, status transitions, Transferticket
    persistence) end-to-end against a stub that always "succeeds" -- it
    must not be exposed as if it performs a real government submission
    until NativeEricClient is implemented.
    """
    filing = _get_owned_filing_or_404(filing_id, current_user, db)

    try:
        filing = submit_filing(db, current_user, filing)
    except SubmissionError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return filing
