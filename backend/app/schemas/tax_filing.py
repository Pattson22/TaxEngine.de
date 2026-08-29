from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import FilingStatus, SubmissionMode


class TaxFilingCreate(BaseModel):
    tax_year: int = Field(ge=2015, le=2100)


class TaxFilingUpdate(BaseModel):
    """Inputs the user supplies before calculation -- currently just the
    Kinderfreibetrag/Kindergeld Günstigerprüfung inputs (§31 EStG). PATCH
    semantics: only supplied fields change."""

    number_of_children: int | None = Field(default=None, ge=0)
    kindergeld_received_cents: int | None = Field(default=None, ge=0)


class TaxFilingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tax_year: int
    status: FilingStatus

    number_of_children: int
    kindergeld_received_cents: int
    kinderfreibetrag_applied: bool | None
    kinderfreibetrag_total_cents: int | None

    estimated_refund_cents: int | None
    taxable_income_cents: int | None
    income_tax_cents: int | None
    solidarity_surcharge_cents: int | None
    church_tax_cents: int | None
    tax_credits_applied_cents: int

    capital_gains_tax_cents: int | None
    capital_gains_soli_cents: int | None
    capital_gains_church_tax_cents: int | None

    net_rental_income_cents: int | None
    net_self_employment_income_cents: int | None

    donation_carryforward_out_cents: int | None

    processing_fee_cents: int
    fee_paid_at: datetime | None

    elster_transfer_ticket: str | None
    elster_submitted_at: datetime | None
    elster_accepted_at: datetime | None
    elster_rejection_reason: str | None

    submission_mode: SubmissionMode
    cover_sheet_generated_at: datetime | None
    cover_sheet_mailed_at: datetime | None

    created_at: datetime
    updated_at: datetime
