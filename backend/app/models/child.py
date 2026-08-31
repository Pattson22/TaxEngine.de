"""SQLAlchemy model for `children` — one row per child a user is claiming
Kinderfreibetrag/Kindergeld for, for a given tax year.

Distinct from (and NOT a replacement for) `tax_filings.number_of_children`
— the plain-count input `tax_engine/kinderfreibetrag.py`'s Günstigerprüfung
still runs on (see that module's docstring for the documented scope
simplification, which this table does not change: no partial-year
eligibility, disabled-child extension, or non-custodial-parent transfer
modeling). These rows exist for a different reason: the real Anlage Kind
in ERiC's E10 schema needs each child's own identity data (name, DOB,
Steuer-ID, Kindschaftsverhältnis) to actually be submitted — see
app/eric/xml_builder.py — which a bare count can never provide. Keeping
the two independent avoids a bigger, riskier change to the existing
Günstigerprüfung input/calculation path than this data model gap requires.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ChildRelationshipType, pg_enum

if TYPE_CHECKING:
    from app.models.user import User


class Child(Base):
    __tablename__ = "children"
    __table_args__ = (
        Index("idx_children_user_year", "user_id", "tax_year"),
        CheckConstraint("tax_year BETWEEN 2015 AND 2100", name="chk_children_tax_year"),
        CheckConstraint(
            "tax_identification_number IS NULL OR tax_identification_number ~ '^\\d{11}$'",
            name="chk_children_steuer_id_format",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tax_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    # E0500108's real documentation is "ggf. abweichender Familienname"
    # (surname, ONLY if different from the filer's own) -- NULL means "same
    # as the filer", not "unknown", matching the real field's own semantics.
    last_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    # Child's own Steuer-ID (E0500406) -- nullable because, like the
    # filer's own tax_identification_number, it's realistically collected
    # progressively rather than required up front.
    tax_identification_number: Mapped[str | None] = mapped_column(Text, nullable=True)

    relationship_type: Mapped[ChildRelationshipType] = mapped_column(
        pg_enum(ChildRelationshipType, "child_relationship_type_enum"),
        nullable=False,
        default=ChildRelationshipType.BIOLOGICAL_OR_ADOPTED,
        server_default="BIOLOGICAL_OR_ADOPTED",
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    user: Mapped["User"] = relationship(back_populates="children")
