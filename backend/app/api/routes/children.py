from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.child import Child
from app.models.user import User
from app.schemas.child import ChildCreate, ChildRead

router = APIRouter(prefix="/children", tags=["children"])


def _get_owned_child_or_404(child_id: uuid.UUID, user: User, db: Session) -> Child:
    child = db.get(Child, child_id)
    if child is None or child.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child not found.")
    return child


@router.post("", response_model=ChildRead, status_code=status.HTTP_201_CREATED)
def create_child(
    payload: ChildCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Child:
    child = Child(user_id=current_user.id, **payload.model_dump())
    db.add(child)
    db.commit()
    db.refresh(child)
    return child


@router.get("", response_model=list[ChildRead])
def list_children(
    tax_year: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Child]:
    query = db.query(Child).filter(Child.user_id == current_user.id)
    if tax_year is not None:
        query = query.filter(Child.tax_year == tax_year)
    return query.order_by(Child.date_of_birth.desc()).all()


@router.get("/{child_id}", response_model=ChildRead)
def get_child(
    child_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Child:
    return _get_owned_child_or_404(child_id, current_user, db)


@router.delete("/{child_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_child(
    child_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    child = _get_owned_child_or_404(child_id, current_user, db)
    db.delete(child)
    db.commit()
