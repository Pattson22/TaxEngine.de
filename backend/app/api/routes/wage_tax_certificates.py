from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_document_extraction_client, get_document_storage
from app.database import get_db
from app.documents.extraction_client import DocumentExtractionClient, DocumentExtractionError
from app.documents.extraction_service import extract_wage_certificate_from_upload
from app.documents.storage import DocumentStorage
from app.models.user import User
from app.models.wage_tax_certificate import WageTaxCertificate
from app.schemas.document_extraction import WageCertificateExtractionResult
from app.schemas.wage_tax_certificate import WageTaxCertificateCreate, WageTaxCertificateRead

router = APIRouter(prefix="/wage-tax-certificates", tags=["wage-tax-certificates"])


@router.post("/extract", response_model=WageCertificateExtractionResult)
async def extract_wage_tax_certificate(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    storage: DocumentStorage = Depends(get_document_storage),
    extraction_client: DocumentExtractionClient = Depends(get_document_extraction_client),
) -> WageCertificateExtractionResult:
    """Reads an uploaded Lohnsteuerbescheinigung (PDF, PNG, JPEG, or .docx)
    and returns the figures it found -- this ONLY prefills the add-employer
    form for the filer to review and correct; it never creates a
    WageTaxCertificate row itself. See app/documents/extraction_service.py."""
    data = await file.read()
    try:
        extraction, storage_key = extract_wage_certificate_from_upload(
            user_id=current_user.id,
            filename=file.filename or "upload",
            content_type=file.content_type or "application/octet-stream",
            data=data,
            storage=storage,
            extraction_client=extraction_client,
        )
    except DocumentExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return WageCertificateExtractionResult(**extraction.model_dump(), source_document_url=storage_key)


def _get_owned_certificate_or_404(
    certificate_id: uuid.UUID, user: User, db: Session
) -> WageTaxCertificate:
    certificate = db.get(WageTaxCertificate, certificate_id)
    if certificate is None or certificate.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wage tax certificate not found.")
    return certificate


@router.post("", response_model=WageTaxCertificateRead, status_code=status.HTTP_201_CREATED)
def create_wage_tax_certificate(
    payload: WageTaxCertificateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WageTaxCertificate:
    certificate = WageTaxCertificate(user_id=current_user.id, **payload.model_dump())
    db.add(certificate)
    db.commit()
    db.refresh(certificate)
    return certificate


@router.get("", response_model=list[WageTaxCertificateRead])
def list_wage_tax_certificates(
    tax_year: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WageTaxCertificate]:
    query = db.query(WageTaxCertificate).filter(WageTaxCertificate.user_id == current_user.id)
    if tax_year is not None:
        query = query.filter(WageTaxCertificate.tax_year == tax_year)
    return query.order_by(WageTaxCertificate.tax_year.desc()).all()


@router.get("/{certificate_id}", response_model=WageTaxCertificateRead)
def get_wage_tax_certificate(
    certificate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WageTaxCertificate:
    return _get_owned_certificate_or_404(certificate_id, current_user, db)


@router.delete("/{certificate_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_wage_tax_certificate(
    certificate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    certificate = _get_owned_certificate_or_404(certificate_id, current_user, db)
    db.delete(certificate)
    db.commit()
