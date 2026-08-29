from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.rental_property_statement import RentalPropertyStatement
from app.models.user import User
from app.schemas.rental_property_statement import RentalPropertyStatementCreate, RentalPropertyStatementRead

router = APIRouter(prefix="/rental-property-statements", tags=["rental-property-statements"])


def _get_owned_statement_or_404(
    statement_id: uuid.UUID, user: User, db: Session
) -> RentalPropertyStatement:
    statement = db.get(RentalPropertyStatement, statement_id)
    if statement is None or statement.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rental property statement not found.")
    return statement


@router.post("", response_model=RentalPropertyStatementRead, status_code=status.HTTP_201_CREATED)
def create_rental_property_statement(
    payload: RentalPropertyStatementCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RentalPropertyStatement:
    statement = RentalPropertyStatement(user_id=current_user.id, **payload.model_dump())
    db.add(statement)
    db.commit()
    db.refresh(statement)
    return statement


@router.get("", response_model=list[RentalPropertyStatementRead])
def list_rental_property_statements(
    tax_year: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RentalPropertyStatement]:
    query = db.query(RentalPropertyStatement).filter(RentalPropertyStatement.user_id == current_user.id)
    if tax_year is not None:
        query = query.filter(RentalPropertyStatement.tax_year == tax_year)
    return query.order_by(RentalPropertyStatement.tax_year.desc()).all()


@router.get("/{statement_id}", response_model=RentalPropertyStatementRead)
def get_rental_property_statement(
    statement_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RentalPropertyStatement:
    return _get_owned_statement_or_404(statement_id, current_user, db)


@router.delete("/{statement_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_rental_property_statement(
    statement_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    statement = _get_owned_statement_or_404(statement_id, current_user, db)
    db.delete(statement)
    db.commit()
