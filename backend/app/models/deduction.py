"""SQLAlchemy model for `deductions` (see db/schema.sql).

`details` is intentionally typed as `dict` (JSONB) rather than broken out
into per-category columns — see the schema.sql table comment for the
category -> expected-keys mapping (e.g. COMMUTE expects
`{"distance_km": ..., "days_worked": ...}`). The calculation orchestration
layer (`app/services/tax_calculation_service.py`) is what actually
interprets this payload per category by calling into `app.tax_engine`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, SmallInteger, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import DeductionCategory, pg_enum

if TYPE_CHECKING:
    from app.models.user import User


class Deduction(Base):
    __tablename__ = "deductions"
    __table_args__ = (
        Index("idx_deductions_user_year_category", "user_id", "tax_year", "category"),
        # GIN index to support querying inside the JSONB payload (e.g. "all
        # commute deductions with distance_km > 30" for anomaly review tooling).
        Index("idx_deductions_details_gin", "details", postgresql_using="gin"),
        CheckConstraint("tax_year BETWEEN 2015 AND 2100", name="chk_deductions_tax_year"),
        CheckConstraint(
            "amount_claimed_cents IS NULL OR amount_claimed_cents >= 0",
            name="chk_deductions_amount_nonneg",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tax_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    category: Mapped[DeductionCategory] = mapped_column(
        pg_enum(DeductionCategory, "deduction_category_enum"), nullable=False
    )
    amount_claimed_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    user: Mapped["User"] = relationship(back_populates="deductions")
