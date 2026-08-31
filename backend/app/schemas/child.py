from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ChildRelationshipType


class ChildCreate(BaseModel):
    tax_year: int = Field(ge=2015, le=2100)
    first_name: str = Field(min_length=1)
    last_name: str | None = None
    date_of_birth: date
    tax_identification_number: str | None = Field(default=None, pattern=r"^\d{11}$")
    relationship_type: ChildRelationshipType = ChildRelationshipType.BIOLOGICAL_OR_ADOPTED


class ChildRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tax_year: int
    first_name: str
    last_name: str | None
    date_of_birth: date
    tax_identification_number: str | None
    relationship_type: ChildRelationshipType
    created_at: datetime
