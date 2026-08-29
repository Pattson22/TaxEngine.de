"""SQLAlchemy model for `capital_income_statements` — one row per bank/
broker Steuerbescheinigung (Anlage KAP), mirroring the
`wage_tax_certificates` pattern for multi-source annual income.
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


class CapitalIncomeStatement(Base):
    __tablename__ = "capital_income_statements"
    __table_args__ = (
        Index("idx_capital_income_user_year", "user_id", "tax_year"),
        CheckConstraint("tax_year BETWEEN 2015 AND 2100", name="chk_capital_income_tax_year"),
        CheckConstraint("gross_income_cents >= 0", name="chk_capital_income_gross_nonneg"),
        CheckConstraint(
            "kapitalertragsteuer_withheld_cents >= 0", name="chk_capital_income_kapest_nonneg"
        ),
        CheckConstraint(
            "solidarity_surcharge_withheld_cents >= 0", name="chk_capital_income_soli_nonneg"
        ),
        CheckConstraint("church_tax_withheld_cents >= 0", name="chk_capital_income_church_nonneg"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tax_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    institution_name: Mapped[str] = mapped_column(Text, nullable=False)

    # Combined interest/dividends/realized gains for the year, as reported
    # on the bank's Steuerbescheinigung -- the Gesamtbetrag input to
    # tax_engine.capital_gains.apply_sparer_pauschbetrag.
    gross_income_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Amounts the bank ALREADY withheld at source (Kapitalertragsteuer +
    # Soli + Kirchensteuer if applicable) -- these feed the refund/back-tax
    # reconciliation the same way wage_tax_certificates' withheld columns do.
    kapitalertragsteuer_withheld_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default=text("0")
    )
    solidarity_surcharge_withheld_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default=text("0")
    )
    church_tax_withheld_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default=text("0")
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    user: Mapped["User"] = relationship(back_populates="capital_income_statements")
