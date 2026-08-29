"""SQLAlchemy model for `wage_tax_certificates` (see db/schema.sql).

Column names mirror the official electronic Lohnsteuerbescheinigung field
semantics — see the schema.sql table comment for the Zeile (line) mapping.
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


class WageTaxCertificate(Base):
    __tablename__ = "wage_tax_certificates"
    __table_args__ = (
        Index("idx_wtc_user_year", "user_id", "tax_year"),
        CheckConstraint("tax_year BETWEEN 2015 AND 2100", name="chk_wtc_tax_year"),
        CheckConstraint("gross_wage_cents >= 0", name="chk_wtc_gross_wage_nonneg"),
        CheckConstraint("income_tax_withheld_cents >= 0", name="chk_wtc_income_tax_nonneg"),
        CheckConstraint("solidarity_surcharge_cents >= 0", name="chk_wtc_soli_nonneg"),
        CheckConstraint("church_tax_withheld_cents >= 0", name="chk_wtc_church_tax_nonneg"),
        CheckConstraint("pension_insurance_employee_cents >= 0", name="chk_wtc_pension_nonneg"),
        CheckConstraint("health_insurance_employee_cents >= 0", name="chk_wtc_health_nonneg"),
        CheckConstraint("long_term_care_insurance_employee_cents >= 0", name="chk_wtc_ltc_nonneg"),
        CheckConstraint("unemployment_insurance_employee_cents >= 0", name="chk_wtc_unemployment_nonneg"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tax_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    employer_name: Mapped[str] = mapped_column(Text, nullable=False)
    employer_tax_number: Mapped[str | None] = mapped_column(Text, nullable=True)

    gross_wage_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    income_tax_withheld_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default=text("0")
    )
    solidarity_surcharge_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default=text("0")
    )
    church_tax_withheld_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default=text("0")
    )

    pension_insurance_employee_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default=text("0")
    )
    health_insurance_employee_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default=text("0")
    )
    long_term_care_insurance_employee_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default=text("0")
    )
    unemployment_insurance_employee_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default=text("0")
    )

    source_document_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    user: Mapped["User"] = relationship(back_populates="wage_tax_certificates")
