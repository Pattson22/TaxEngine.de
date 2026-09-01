from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import EricSubmissionJobStatus


class EricSubmissionJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tax_filing_id: uuid.UUID
    status: EricSubmissionJobStatus
    is_amendment: bool
    error_message: str | None
    transfer_ticket: str | None
    claimed_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
