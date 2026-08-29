"""SQLAlchemy model for the `users` table (see db/schema.sql)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ChurchTaxType, FederalState, TaxClass, pg_enum

if TYPE_CHECKING:
    from app.models.capital_income_statement import CapitalIncomeStatement
    from app.models.deduction import Deduction
    from app.models.rental_property_statement import RentalPropertyStatement
    from app.models.self_employment_statement import SelfEmploymentStatement
    from app.models.tax_filing import TaxFiling
    from app.models.wage_tax_certificate import WageTaxCertificate


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        # Partial index for active-user email lookups (the UNIQUE
        # constraint on `email` below covers correctness; this covers
        # lookup performance while excluding soft-deleted rows).
        Index("idx_users_email", "email", postgresql_where=text("deleted_at IS NULL")),
        CheckConstraint(
            "tax_identification_number IS NULL OR tax_identification_number ~ '^\\d{11}$'",
            name="chk_steuer_id_format",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    tax_identification_number: Mapped[str | None] = mapped_column(Text, nullable=True)

    residence_state: Mapped[FederalState] = mapped_column(
        pg_enum(FederalState, "federal_state_enum"), nullable=False
    )
    tax_class: Mapped[TaxClass] = mapped_column(
        pg_enum(TaxClass, "tax_class_enum"), nullable=False, default=TaxClass.I, server_default="I"
    )
    church_tax_type: Mapped[ChurchTaxType] = mapped_column(
        pg_enum(ChurchTaxType, "church_tax_type_enum"),
        nullable=False,
        default=ChurchTaxType.NONE,
        server_default="NONE",
    )
    is_joint_assessment: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    spouse_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    spouse: Mapped["User | None"] = relationship("User", remote_side=[id])
    wage_tax_certificates: Mapped[list["WageTaxCertificate"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    capital_income_statements: Mapped[list["CapitalIncomeStatement"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    rental_property_statements: Mapped[list["RentalPropertyStatement"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    self_employment_statements: Mapped[list["SelfEmploymentStatement"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    deductions: Mapped[list["Deduction"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    tax_filings: Mapped[list["TaxFiling"]] = relationship(back_populates="user", cascade="all, delete-orphan")
