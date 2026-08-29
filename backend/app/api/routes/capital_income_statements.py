from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.capital_income_statement import CapitalIncomeStatement
from app.models.user import User
from app.schemas.capital_income_statement import CapitalIncomeStatementCreate, CapitalIncomeStatementRead

router = APIRouter(prefix="/capital-income-statements", tags=["capital-income-statements"])


def _get_owned_statement_or_404(
    statement_id: uuid.UUID, user: User, db: Session
) -> CapitalIncomeStatement:
    statement = db.get(CapitalIncomeStatement, statement_id)
    if statement is None or statement.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capital income statement not found.")
    return statement


@router.post("", response_model=CapitalIncomeStatementRead, status_code=status.HTTP_201_CREATED)
def create_capital_income_statement(
    payload: CapitalIncomeStatementCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CapitalIncomeStatement:
    statement = CapitalIncomeStatement(user_id=current_user.id, **payload.model_dump())
    db.add(statement)
    db.commit()
    db.refresh(statement)
    return statement


@router.get("", response_model=list[CapitalIncomeStatementRead])
def list_capital_income_statements(
    tax_year: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CapitalIncomeStatement]:
    query = db.query(CapitalIncomeStatement).filter(CapitalIncomeStatement.user_id == current_user.id)
    if tax_year is not None:
        query = query.filter(CapitalIncomeStatement.tax_year == tax_year)
    return query.order_by(CapitalIncomeStatement.tax_year.desc()).all()


@router.get("/{statement_id}", response_model=CapitalIncomeStatementRead)
def get_capital_income_statement(
    statement_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CapitalIncomeStatement:
    return _get_owned_statement_or_404(statement_id, current_user, db)


@router.delete("/{statement_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_capital_income_statement(
    statement_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    statement = _get_owned_statement_or_404(statement_id, current_user, db)
    db.delete(statement)
    db.commit()
