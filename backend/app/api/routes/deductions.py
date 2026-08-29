from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.deduction import Deduction
from app.models.user import User
from app.schemas.deduction import DeductionCreate, DeductionRead

router = APIRouter(prefix="/deductions", tags=["deductions"])


def _get_owned_deduction_or_404(deduction_id: uuid.UUID, user: User, db: Session) -> Deduction:
    deduction = db.get(Deduction, deduction_id)
    if deduction is None or deduction.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deduction not found.")
    return deduction


@router.post("", response_model=DeductionRead, status_code=status.HTTP_201_CREATED)
def create_deduction(
    payload: DeductionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Deduction:
    deduction = Deduction(user_id=current_user.id, **payload.model_dump())
    db.add(deduction)
    db.commit()
    db.refresh(deduction)
    return deduction


@router.get("", response_model=list[DeductionRead])
def list_deductions(
    tax_year: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Deduction]:
    query = db.query(Deduction).filter(Deduction.user_id == current_user.id)
    if tax_year is not None:
        query = query.filter(Deduction.tax_year == tax_year)
    return query.order_by(Deduction.tax_year.desc(), Deduction.created_at.desc()).all()


@router.get("/{deduction_id}", response_model=DeductionRead)
def get_deduction(
    deduction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Deduction:
    return _get_owned_deduction_or_404(deduction_id, current_user, db)


@router.delete("/{deduction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deduction(
    deduction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    deduction = _get_owned_deduction_or_404(deduction_id, current_user, db)
    db.delete(deduction)
    db.commit()
