from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.enums import FilingStatus
from app.models.tax_filing import TaxFiling
from app.models.user import User
from app.schemas.tax_filing import TaxFilingCreate, TaxFilingRead
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


@router.post("/{filing_id}/pay", response_model=TaxFilingRead)
def mark_filing_fee_paid(
    filing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaxFiling:
    """Placeholder for the payment-provider webhook flow: marks the flat
    €34.90 processing fee as paid. A real implementation verifies a Stripe/
    Adyen webhook signature and records `payment_provider_ref` here instead
    of trusting a bare client call — this endpoint exists only so the
    filing-status state machine (DRAFT -> CALCULATED -> FEE_PAID ->
    SUBMITTED) has a place to transition, and must not be exposed
    unauthenticated/unverified in production."""
    filing = _get_owned_filing_or_404(filing_id, current_user, db)

    if filing.status != FilingStatus.CALCULATED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Filing must be calculated before the fee can be marked as paid.",
        )

    filing.status = FilingStatus.FEE_PAID
    filing.fee_paid_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(filing)
    return filing
