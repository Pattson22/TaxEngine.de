from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import ChurchTaxType, FederalState, TaxClass


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, description="Minimum 12 characters.")
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    residence_state: FederalState
    tax_class: TaxClass = TaxClass.I
    church_tax_type: ChurchTaxType = ChurchTaxType.NONE
    is_joint_assessment: bool = False


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """All fields optional — PATCH semantics, only supplied fields change."""

    first_name: str | None = Field(default=None, min_length=1)
    last_name: str | None = Field(default=None, min_length=1)
    residence_state: FederalState | None = None
    tax_class: TaxClass | None = None
    church_tax_type: ChurchTaxType | None = None
    is_joint_assessment: bool | None = None
    tax_identification_number: str | None = Field(default=None, pattern=r"^\d{11}$")


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    tax_identification_number: str | None
    residence_state: FederalState
    tax_class: TaxClass
    church_tax_type: ChurchTaxType
    is_joint_assessment: bool
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
