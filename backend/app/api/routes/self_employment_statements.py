from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.self_employment_statement import SelfEmploymentStatement
from app.models.user import User
from app.schemas.self_employment_statement import (
    SelfEmploymentStatementCreate,
    SelfEmploymentStatementRead,
)

router = APIRouter(prefix="/self-employment-statements", tags=["self-employment-statements"])


def _get_owned_statement_or_404(
    statement_id: uuid.UUID, user: User, db: Session
) -> SelfEmploymentStatement:
    statement = db.get(SelfEmploymentStatement, statement_id)
    if statement is None or statement.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Self-employment statement not found."
        )
    return statement


@router.post("", response_model=SelfEmploymentStatementRead, status_code=status.HTTP_201_CREATED)
def create_self_employment_statement(
    payload: SelfEmploymentStatementCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SelfEmploymentStatement:
    statement = SelfEmploymentStatement(user_id=current_user.id, **payload.model_dump())
    db.add(statement)
    db.commit()
    db.refresh(statement)
    return statement


@router.get("", response_model=list[SelfEmploymentStatementRead])
def list_self_employment_statements(
    tax_year: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SelfEmploymentStatement]:
    query = db.query(SelfEmploymentStatement).filter(SelfEmploymentStatement.user_id == current_user.id)
    if tax_year is not None:
        query = query.filter(SelfEmploymentStatement.tax_year == tax_year)
    return query.order_by(SelfEmploymentStatement.tax_year.desc()).all()


@router.get("/{statement_id}", response_model=SelfEmploymentStatementRead)
def get_self_employment_statement(
    statement_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SelfEmploymentStatement:
    return _get_owned_statement_or_404(statement_id, current_user, db)


@router.delete("/{statement_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_self_employment_statement(
    statement_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    statement = _get_owned_statement_or_404(statement_id, current_user, db)
    db.delete(statement)
    db.commit()
