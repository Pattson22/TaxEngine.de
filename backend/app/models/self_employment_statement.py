"""SQLAlchemy model for `self_employment_statements` — one row per
business/year (simplified EÜR, §15/§18 EStG), mirroring the
rental_property_statements pattern: insert/delete-only, signed net result
computed in tax_engine, no withholding concept.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class SelfEmploymentStatement(Base):
    __tablename__ = "self_employment_statements"
    __table_args__ = (
        Index("idx_self_employment_user_year", "user_id", "tax_year"),
        CheckConstraint("tax_year BETWEEN 2015 AND 2100", name="chk_self_employment_tax_year"),
        CheckConstraint("gross_revenue_cents >= 0", name="chk_self_employment_revenue_nonneg"),
        CheckConstraint(
            "deductible_expenses_cents >= 0", name="chk_self_employment_expenses_nonneg"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tax_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    business_name: Mapped[str] = mapped_column(Text, nullable=False)

    gross_revenue_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Documented Betriebsausgaben (operating expenses) -- see
    # tax_engine/self_employment_income.py's module docstring for the
    # Gewerbesteuer scope limitation.
    deductible_expenses_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default=text("0")
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    user: Mapped["User"] = relationship(back_populates="self_employment_statements")
