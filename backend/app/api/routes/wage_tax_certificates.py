from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.wage_tax_certificate import WageTaxCertificate
from app.schemas.wage_tax_certificate import WageTaxCertificateCreate, WageTaxCertificateRead

router = APIRouter(prefix="/wage-tax-certificates", tags=["wage-tax-certificates"])


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


@router.delete("/{certificate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_wage_tax_certificate(
    certificate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    certificate = _get_owned_certificate_or_404(certificate_id, current_user, db)
    db.delete(certificate)
    db.commit()
