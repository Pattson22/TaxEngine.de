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

    # Derived server-side (see the route's _to_read) so no client has to
    # re-implement the §7 Abs. 4 AfA rate table to display a correct
    # figure. Legal constants live in tax_engine/constants.py and nowhere
    # else -- a TypeScript copy of that table would be a second source of
    # truth to keep in sync every time the law changes.
    afa_deduction_cents: int
    total_deductible_expenses_cents: int
    net_rental_income_cents: int
