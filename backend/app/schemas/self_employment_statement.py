from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SelfEmploymentStatementCreate(BaseModel):
    tax_year: int = Field(ge=2015, le=2100)
    business_name: str = Field(min_length=1)
    gross_revenue_cents: int = Field(ge=0)
    deductible_expenses_cents: int = Field(default=0, ge=0)


class SelfEmploymentStatementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tax_year: int
    business_name: str
    gross_revenue_cents: int
    deductible_expenses_cents: int
    created_at: datetime
