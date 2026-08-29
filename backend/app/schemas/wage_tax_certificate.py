from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WageTaxCertificateCreate(BaseModel):
    tax_year: int = Field(ge=2015, le=2100)
    employer_name: str = Field(min_length=1)
    employer_tax_number: str | None = None

    gross_wage_cents: int = Field(ge=0)
    income_tax_withheld_cents: int = Field(default=0, ge=0)
    solidarity_surcharge_cents: int = Field(default=0, ge=0)
    church_tax_withheld_cents: int = Field(default=0, ge=0)

    pension_insurance_employee_cents: int = Field(default=0, ge=0)
    health_insurance_employee_cents: int = Field(default=0, ge=0)
    long_term_care_insurance_employee_cents: int = Field(default=0, ge=0)
    unemployment_insurance_employee_cents: int = Field(default=0, ge=0)

    source_document_url: str | None = None


class WageTaxCertificateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tax_year: int
    employer_name: str
    employer_tax_number: str | None
    gross_wage_cents: int
    income_tax_withheld_cents: int
    solidarity_surcharge_cents: int
    church_tax_withheld_cents: int
    pension_insurance_employee_cents: int
    health_insurance_employee_cents: int
    long_term_care_insurance_employee_cents: int
    unemployment_insurance_employee_cents: int
    source_document_url: str | None
    created_at: datetime
