"""SQLAlchemy model for the `users` table (see db/schema.sql)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ChurchTaxType, FederalState, TaxClass, pg_enum

if TYPE_CHECKING:
    from app.models.capital_income_statement import CapitalIncomeStatement
    from app.models.child import Child
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
        CheckConstraint(
            "postal_code IS NULL OR postal_code ~ '^\\d{5}$'",
            name="chk_users_postal_code_format",
        ),
        CheckConstraint(
            "finanzamt_bufa_nummer IS NULL OR finanzamt_bufa_nummer ~ '^\\d{4}$'",
            name="chk_users_bufa_nummer_format",
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

    # Onboarding profile -- collected in a mandatory post-login step
    # (frontend `/onboarding`), not at registration. All nullable at the
    # DB layer since existing rows predate this; `nullable=True` here is
    # a storage fact, not a statement that the app treats them as
    # optional -- see the frontend's isProfileComplete() gate.
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    street: Mapped[str | None] = mapped_column(Text, nullable=True)
    house_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    postal_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Steuernummer (Finanzamt-issued, changes when you move) -- distinct
    # from tax_identification_number (Steuer-ID, permanent, national).
    # ELSTER submissions need both. Format varies by Bundesland (digit
    # count and slash grouping differ), so unlike Steuer-ID this has no
    # single regex to validate against.
    steuernummer: Mapped[str | None] = mapped_column(Text, nullable=True)
    # The filer's Finanzamt's 4-digit Bundesfinanzamtsnummer -- REQUIRED by
    # the real ELSTER transfer envelope (NutzdatenHeader's
    # Empfaenger id="F", see app/eric/xml_builder.py's module docstring)
    # but distinct from steuernummer (that's the taxpayer's own number AT
    # that Finanzamt; this is which Finanzamt). Format confirmed against
    # the SDK's own BUFANrSType (headerbasis_datentypen.xsd): always
    # exactly 4 digits, first two identifying the Bundesland cluster.
    finanzamt_bufa_nummer: Mapped[str | None] = mapped_column(Text, nullable=True)

    # § 5 Abs. 1 of the ERiC-Lizenzvereinbarung (see
    # docs/ELSTER_ERIC_INTEGRATION.md section 8) requires presenting the
    # Finanzverwaltung's own DSGVO Art. 12-14 info letter
    # (frontend `/elster-datenschutzhinweis`) before the user uses the
    # software, with the ability to confirm having read it -- set once,
    # server-side, by POST /users/me/confirm-elster-privacy-notice (never
    # client-suppliable via a raw timestamp, same reasoning as
    # TaxFiling.withdrawal_consent_at).
    elster_privacy_notice_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

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
    children: Mapped[list["Child"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    deductions: Mapped[list["Deduction"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    tax_filings: Mapped[list["TaxFiling"]] = relationship(back_populates="user", cascade="all, delete-orphan")
