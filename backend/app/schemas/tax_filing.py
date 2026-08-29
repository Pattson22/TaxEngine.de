from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import FilingStatus


class TaxFilingCreate(BaseModel):
    tax_year: int = Field(ge=2015, le=2100)


class TaxFilingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tax_year: int
    status: FilingStatus

    estimated_refund_cents: int | None
    taxable_income_cents: int | None
    income_tax_cents: int | None
    solidarity_surcharge_cents: int | None
    church_tax_cents: int | None
    tax_credits_applied_cents: int

    processing_fee_cents: int
    fee_paid_at: datetime | None

    elster_transfer_ticket: str | None
    elster_submitted_at: datetime | None
    elster_accepted_at: datetime | None
    elster_rejection_reason: str | None

    created_at: datetime
    updated_at: datetime
