"""SQLAlchemy model for `rental_property_statements` — one row per rental
property/year (Einkünfte aus Vermietung und Verpachtung, §21 EStG),
mirroring the wage_tax_certificates / capital_income_statements pattern
for multi-source annual income: insert/delete-only (no updated_at/PATCH),
and no "withheld" concept, since rental income is never subject to
withholding tax — it flows entirely through the annual assessment.
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


class RentalPropertyStatement(Base):
    __tablename__ = "rental_property_statements"
    __table_args__ = (
        Index("idx_rental_property_user_year", "user_id", "tax_year"),
        CheckConstraint("tax_year BETWEEN 2015 AND 2100", name="chk_rental_property_tax_year"),
        CheckConstraint("gross_rental_income_cents >= 0", name="chk_rental_property_income_nonneg"),
        CheckConstraint(
            "deductible_expenses_cents >= 0", name="chk_rental_property_expenses_nonneg"
        ),
        CheckConstraint(
            "building_acquisition_cost_cents IS NULL OR building_acquisition_cost_cents >= 0",
            name="chk_rental_property_building_cost_nonneg",
        ),
        CheckConstraint(
            "building_completion_year IS NULL "
            "OR building_completion_year BETWEEN 1800 AND 2100",
            name="chk_rental_property_completion_year_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tax_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    property_address: Mapped[str] = mapped_column(Text, nullable=False)

    gross_rental_income_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Documented Werbungskosten bei V+V (AfA, mortgage interest, repairs,
    # management fees, ...) -- see tax_engine/rental_income.py's module
    # docstring for the scope limitation on AfA schedule calculation.
    deductible_expenses_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default=text("0")
    )

    # Optional structured AfA input (§7 Abs. 4 EStG, see tax_engine/afa.py)
    # -- BOTH must be set for AfA to be computed automatically and ADDED on
    # top of deductible_expenses_cents above. When either is NULL (the
    # default), deductible_expenses_cents is treated as the complete
    # Werbungskosten figure, matching this project's original behavior
    # where any AfA had to be pre-computed and folded in manually --
    # see tax_calculation_service.rental_total_deductible_expenses_cents()
    # for exactly how the two paths differ. That helper is the ONE place
    # the rule lives: both the calculation pipeline and the Anlage V
    # serializer (app/eric/xml_builder.py) read the total through it, so
    # the refund estimate and the submitted return can never diverge.
    building_acquisition_cost_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    building_completion_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    user: Mapped["User"] = relationship(back_populates="rental_property_statements")
