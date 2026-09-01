from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.eric.cover_sheet import build_cover_sheet_pdf
from app.eric.submission_service import enqueue_submission
from app.models.enums import FilingStatus, SubmissionMode
from app.models.eric_submission_job import EricSubmissionJob
from app.models.tax_filing import TaxFiling
from app.models.user import User
from app.schemas.eric_submission_job import EricSubmissionJobRead
from app.schemas.payment import PaymentIntentRequest, PaymentIntentResponse
from app.schemas.tax_filing import TaxFilingCreate, TaxFilingRead, TaxFilingUpdate
from app.services.payment_service import PaymentError, create_payment_intent_for_filing
from app.services.tax_calculation_service import calculate_tax_filing, get_supported_tax_years

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
    supported_years = get_supported_tax_years()
    if payload.tax_year not in supported_years:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"No verified tax constants available for tax_year={payload.tax_year}. "
                f"Supported years: {supported_years}."
            ),
        )

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


@router.get("/supported-years", response_model=list[int])
def list_supported_tax_years() -> list[int]:
    """Tax years the calculation engine has reviewed, published constants
    for. The frontend's year picker sources its options from here so it
    can never drift out of sync with tax_engine/constants.py. Registered
    ahead of GET /{filing_id} so "supported-years" isn't swallowed as a
    (invalid) filing_id path parameter."""
    return get_supported_tax_years()


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
    except ValueError as exc:
        # ValueError, not just TaxCalculationError: get_constants_for_year()
        # (called throughout tax_engine) raises a plain ValueError for any
        # tax_year outside SUPPORTED_TAX_YEARS, which TaxFilingCreate's
        # 2015-2100 range allows callers to create a filing for.
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    db.commit()
    db.refresh(filing)
    return filing


@router.post("/{filing_id}/payment-intent", response_model=PaymentIntentResponse)
def create_filing_payment_intent(
    filing_id: uuid.UUID,
    body: PaymentIntentRequest,
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

    # Recording withdrawal_consent_at is what makes the § 356 Abs. 4 BGB
    # early expiry of the statutory withdrawal right (AGB § 5) effective
    # -- the consent must be given before payment, so this must happen
    # before create_payment_intent_for_filing, not after. Only required
    # the first time: a retried/failed payment attempt on the same
    # filing already has consent on record.
    if filing.withdrawal_consent_at is None:
        if not body.withdrawal_consent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must consent to immediate performance before paying.",
            )
        filing.withdrawal_consent_at = datetime.now(timezone.utc)

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


@router.post(
    "/{filing_id}/submit", response_model=EricSubmissionJobRead, status_code=status.HTTP_202_ACCEPTED
)
def submit_tax_filing(
    filing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EricSubmissionJob:
    """Queue a FEE_PAID filing for ELSTER submission.

    Submission itself happens out-of-process: this only inserts a PENDING
    `EricSubmissionJob` row for the separate `eric-submitter` worker
    (app/eric_submitter/worker.py) to claim and process against the real
    NativeEricClient -- see docs/ELSTER_ERIC_INTEGRATION.md section 2 for
    why ERiC must never load inside this web process. Poll
    GET /{filing_id}/submission-job for the job's outcome; once it
    SUCCEEDED, GET /{filing_id} reflects the filing's updated status and
    elster_transfer_ticket.

    The checks here (FEE_PAID, Steuer-ID present) exist purely to fail
    fast with a useful error -- the worker re-verifies both itself before
    actually submitting, since a queued job can sit for a while.

    Every filing submits in SubmissionMode.KOMPRIMIERT (the only mode
    implemented): once ACCEPTED, GET /{filing_id}/cover-sheet and
    POST /{filing_id}/mark-mailed complete the paper half of the filing.
    """
    filing = _get_owned_filing_or_404(filing_id, current_user, db)

    if filing.status != FilingStatus.FEE_PAID:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Filing must be FEE_PAID before submission (current status: {filing.status.value}).",
        )
    if not current_user.tax_identification_number:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No tax_identification_number (Steuer-ID) on file -- required for ELSTER submission.",
        )

    return enqueue_submission(db, filing)


@router.get("/{filing_id}/submission-job", response_model=EricSubmissionJobRead)
def get_submission_job(
    filing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EricSubmissionJob:
    """The most recent submission attempt for this filing -- what the
    frontend polls after POST /{filing_id}/submit to learn whether the
    eric-submitter worker has picked the job up yet, and whether it
    succeeded or failed."""
    filing = _get_owned_filing_or_404(filing_id, current_user, db)

    job = (
        db.query(EricSubmissionJob)
        .filter(EricSubmissionJob.tax_filing_id == filing.id)
        .order_by(EricSubmissionJob.created_at.desc())
        .first()
    )
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No submission has been queued for this filing yet."
        )
    return job


@router.get("/{filing_id}/submission-jobs", response_model=list[EricSubmissionJobRead])
def list_submission_jobs(
    filing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EricSubmissionJob]:
    """Every submission attempt ever queued for this filing, newest first
    -- the permanent audit trail an amendment relies on, since
    `TaxFiling.elster_transfer_ticket` etc. only ever reflect the CURRENT
    attempt (calculate_tax_filing clears them when a submitted filing gets
    recalculated for an amendment -- see that function's docstring). Each
    job's own `is_amendment` flag distinguishes the original submission
    from any later corrections."""
    filing = _get_owned_filing_or_404(filing_id, current_user, db)

    return (
        db.query(EricSubmissionJob)
        .filter(EricSubmissionJob.tax_filing_id == filing.id)
        .order_by(EricSubmissionJob.created_at.desc())
        .all()
    )


@router.get("/{filing_id}/cover-sheet")
def get_cover_sheet(
    filing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Download the KOMPRIMIERT cover sheet PDF -- see
    app/eric/cover_sheet.py's module docstring for what this is and isn't.
    Requires the filing to have actually been submitted (SUBMITTED,
    ACCEPTED, or REJECTED all have a Transferticket to reference)."""
    filing = _get_owned_filing_or_404(filing_id, current_user, db)

    if filing.submission_mode != SubmissionMode.KOMPRIMIERT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This filing isn't using KOMPRIMIERT submission -- no cover sheet applies.",
        )
    if filing.status not in (FilingStatus.SUBMITTED, FilingStatus.ACCEPTED, FilingStatus.REJECTED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Submit this filing to ELSTER before downloading its cover sheet.",
        )

    pdf_bytes = build_cover_sheet_pdf(current_user, filing)

    if filing.cover_sheet_generated_at is None:
        filing.cover_sheet_generated_at = datetime.now(timezone.utc)
        db.commit()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="komprimierte-steuererklaerung-{filing.tax_year}.pdf"'
            )
        },
    )


@router.post("/{filing_id}/mark-mailed", response_model=TaxFilingRead)
def mark_cover_sheet_mailed(
    filing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaxFiling:
    """Record the taxpayer's own attestation that they printed, signed,
    and mailed the cover sheet -- see TaxFiling.cover_sheet_mailed_at's
    docstring for why this is a UI checklist item, not a verified fact."""
    filing = _get_owned_filing_or_404(filing_id, current_user, db)

    if filing.cover_sheet_generated_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Download the cover sheet before marking it as mailed.",
        )

    filing.cover_sheet_mailed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(filing)
    return filing
