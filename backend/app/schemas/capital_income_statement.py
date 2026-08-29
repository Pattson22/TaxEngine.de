from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CapitalIncomeStatementCreate(BaseModel):
    tax_year: int = Field(ge=2015, le=2100)
    institution_name: str = Field(min_length=1)
    gross_income_cents: int = Field(ge=0)
    kapitalertragsteuer_withheld_cents: int = Field(default=0, ge=0)
    solidarity_surcharge_withheld_cents: int = Field(default=0, ge=0)
    church_tax_withheld_cents: int = Field(default=0, ge=0)


class CapitalIncomeStatementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tax_year: int
    institution_name: str
    gross_income_cents: int
    kapitalertragsteuer_withheld_cents: int
    solidarity_surcharge_withheld_cents: int
    church_tax_withheld_cents: int
    created_at: datetime
