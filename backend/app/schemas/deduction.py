"""
Pydantic schemas for the `deductions` API resource.

`details` is stored as a loosely-typed dict (it round-trips into JSONB
regardless of category), but for categories with a known shape,
`DeductionCreate` validates it against the matching `*Details` model below
at WRITE time (via a model_validator) — so a malformed payload (e.g. a
string where `distance_km` should be an int) is rejected with a 422 the
moment the user submits it, not later when they hit "calculate". The
calculation orchestration layer (`app/services/tax_calculation_service.py`)
re-validates the same way as defense-in-depth for any caller that bypasses
this API schema (e.g. a future batch/import job).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.models.enums import DeductionCategory

# Categories whose `details` are numerically computed by app.tax_engine
# rather than trusted from `amount_claimed_cents` — see the schema.sql
# `deductions` table comment for the same list.
COMPUTED_CATEGORIES = frozenset({
    DeductionCategory.COMMUTE,
    DeductionCategory.HOME_OFFICE,
    DeductionCategory.DONATIONS,
    DeductionCategory.CHILDCARE,
    DeductionCategory.HANDWERKERLEISTUNGEN,
})


class CommuteDetails(BaseModel):
    distance_km: int = Field(ge=0)
    days_worked: int = Field(ge=0)


class HomeOfficeDetails(BaseModel):
    days_claimed: int = Field(ge=0)


class DonationDetails(BaseModel):
    amount_donated_cents: int = Field(ge=0)


class ChildcareDetails(BaseModel):
    total_costs_cents: int = Field(ge=0)
    number_of_children: int = Field(ge=0)


class HandwerkerleistungenDetails(BaseModel):
    labor_cost_cents: int = Field(ge=0)


# category -> the model its `details` payload must validate against. Kept
# next to the models themselves so adding a new computed category can't
# forget to wire up write-time validation for it.
_CATEGORY_DETAIL_MODELS: dict[DeductionCategory, type[BaseModel]] = {
    DeductionCategory.COMMUTE: CommuteDetails,
    DeductionCategory.HOME_OFFICE: HomeOfficeDetails,
    DeductionCategory.DONATIONS: DonationDetails,
    DeductionCategory.CHILDCARE: ChildcareDetails,
    DeductionCategory.HANDWERKERLEISTUNGEN: HandwerkerleistungenDetails,
}


class DeductionCreate(BaseModel):
    tax_year: int = Field(ge=2015, le=2100)
    category: DeductionCategory
    amount_claimed_cents: int | None = Field(default=None, ge=0)
    details: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_details_match_category(self) -> "DeductionCreate":
        detail_model = _CATEGORY_DETAIL_MODELS.get(self.category)
        if detail_model is None:
            # WORK_EQUIPMENT, FURTHER_EDUCATION, DOUBLE_HOUSEHOLD, INSURANCE,
            # OTHER have no fixed `details` shape -- any dict is accepted.
            return self

        try:
            detail_model.model_validate(self.details)
        except ValidationError as exc:
            raise ValueError(
                f"`details` is invalid for category={self.category.value}: {exc}"
            ) from exc

        return self


class DeductionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tax_year: int
    category: DeductionCategory
    amount_claimed_cents: int | None
    details: dict[str, Any]
    created_at: datetime
    updated_at: datetime
