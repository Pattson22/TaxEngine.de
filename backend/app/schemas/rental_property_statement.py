from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RentalPropertyStatementCreate(BaseModel):
    tax_year: int = Field(ge=2015, le=2100)
    property_address: str = Field(min_length=1)
    gross_rental_income_cents: int = Field(ge=0)
    deductible_expenses_cents: int = Field(default=0, ge=0)
    building_acquisition_cost_cents: int | None = Field(default=None, ge=0)
    building_completion_year: int | None = Field(default=None, ge=1800, le=2100)


class RentalPropertyStatementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tax_year: int
    property_address: str
    gross_rental_income_cents: int
    deductible_expenses_cents: int
    building_acquisition_cost_cents: int | None
    building_completion_year: int | None
    created_at: datetime
