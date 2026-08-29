"""SQLAlchemy model for `tax_filings` (see db/schema.sql)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import FilingStatus, pg_enum

if TYPE_CHECKING:
    from app.models.user import User


class TaxFiling(Base):
    __tablename__ = "tax_filings"
    __table_args__ = (
        UniqueConstraint("user_id", "tax_year", name="uq_filings_user_year"),
        Index("idx_filings_status", "status"),
        CheckConstraint("tax_year BETWEEN 2015 AND 2100", name="chk_filings_tax_year"),
        CheckConstraint(
            "income_tax_cents IS NULL OR income_tax_cents >= 0", name="chk_filings_income_tax_nonneg"
        ),
        CheckConstraint(
            "solidarity_surcharge_cents IS NULL OR solidarity_surcharge_cents >= 0",
            name="chk_filings_soli_nonneg",
        ),
        CheckConstraint(
            "church_tax_cents IS NULL OR church_tax_cents >= 0", name="chk_filings_church_tax_nonneg"
        ),
        CheckConstraint("tax_credits_applied_cents >= 0", name="chk_filings_credits_nonneg"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tax_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[FilingStatus] = mapped_column(
        pg_enum(FilingStatus, "filing_status_enum"),
        nullable=False,
        default=FilingStatus.DRAFT,
        server_default="DRAFT",
    )

    estimated_refund_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    taxable_income_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    income_tax_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    solidarity_surcharge_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    church_tax_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tax_credits_applied_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default=text("0")
    )

    processing_fee_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=3490, server_default=text("3490")
    )
    fee_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_provider_ref: Mapped[str | None] = mapped_column(Text, nullable=True)

    elster_transfer_ticket: Mapped[str | None] = mapped_column(Text, nullable=True)
    elster_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    elster_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    elster_rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    user: Mapped["User"] = relationship(back_populates="tax_filings")
