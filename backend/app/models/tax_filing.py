"""SQLAlchemy model for `tax_filings` (see db/schema.sql)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
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
from app.models.enums import FilingStatus, SubmissionMode, pg_enum

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
        CheckConstraint(
            "capital_gains_tax_cents IS NULL OR capital_gains_tax_cents >= 0",
            name="chk_filings_capital_gains_tax_nonneg",
        ),
        CheckConstraint(
            "capital_gains_soli_cents IS NULL OR capital_gains_soli_cents >= 0",
            name="chk_filings_capital_gains_soli_nonneg",
        ),
        CheckConstraint(
            "capital_gains_church_tax_cents IS NULL OR capital_gains_church_tax_cents >= 0",
            name="chk_filings_capital_gains_church_tax_nonneg",
        ),
        CheckConstraint("number_of_children >= 0", name="chk_filings_children_nonneg"),
        CheckConstraint(
            "kindergeld_received_cents >= 0", name="chk_filings_kindergeld_nonneg"
        ),
        CheckConstraint(
            "kinderfreibetrag_total_cents IS NULL OR kinderfreibetrag_total_cents >= 0",
            name="chk_filings_kinderfreibetrag_nonneg",
        ),
        CheckConstraint(
            "donation_carryforward_out_cents IS NULL OR donation_carryforward_out_cents >= 0",
            name="chk_filings_donation_carryforward_nonneg",
        ),
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

    # INPUT fields for the Kinderfreibetrag/Kindergeld Günstigerprüfung
    # (§31 EStG, see tax_engine/kinderfreibetrag.py) -- unlike every other
    # field below this point, these are supplied BY THE USER (via
    # PATCH /tax-filings/{id}) before calculation, not computed by it.
    number_of_children: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default=text("0")
    )
    kindergeld_received_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default=text("0")
    )

    estimated_refund_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    taxable_income_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    income_tax_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    solidarity_surcharge_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    church_tax_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tax_credits_applied_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default=text("0")
    )

    # OUTPUT of the Günstigerprüfung -- which path the Finanzamt-equivalent
    # comparison chose, and the allowance amount that was compared against
    # Kindergeld (populated even when NOT applied, for UI transparency).
    kinderfreibetrag_applied: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    kinderfreibetrag_total_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Capital gains (Abgeltungsteuer, §32d EStG) is a legally SEPARATE tax
    # regime from the veranlagte Einkommensteuer above -- kept as its own
    # line items rather than folded into income_tax_cents/solidarity_
    # surcharge_cents/church_tax_cents, so every number here still traces
    # back to a distinct form/legal basis (see tax_engine/capital_gains.py).
    capital_gains_tax_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    capital_gains_soli_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    capital_gains_church_tax_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Net Einkünfte aus Vermietung und Verpachtung (§21 EStG) across all of
    # the user's rental_property_statements for the year -- see
    # tax_engine/rental_income.py. Deliberately has NO non-negativity
    # CHECK constraint: a documented rental loss is a legitimate negative
    # value that already fed into taxable_income_cents above, and hiding
    # its sign here would make the breakdown misleading.
    net_rental_income_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Net self-employment income (§15/§18 EStG, simplified EÜR) -- same
    # "signed, no CHECK constraint" treatment as net_rental_income_cents
    # above, and the same Gewerbesteuer scope caveat documented in
    # tax_engine/self_employment_income.py.
    net_self_employment_income_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Spendenvortrag (§10b Abs. 1 Satz 9 EStG) -- the unused portion of
    # this year's donations (own + any carried-in balance) that exceeds
    # the 20% cap and carries forward to NEXT year. There is deliberately
    # no "..._in_cents" column: the incoming balance for year Y is simply
    # year Y-1's filing row's carryforward_out_cents, looked up at
    # calculation time (see tax_calculation_service.py) rather than
    # duplicated storage that could drift out of sync.
    donation_carryforward_out_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    processing_fee_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=3490, server_default=text("3490")
    )
    fee_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_provider_ref: Mapped[str | None] = mapped_column(Text, nullable=True)

    elster_transfer_ticket: Mapped[str | None] = mapped_column(Text, nullable=True)
    elster_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    elster_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    elster_rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # See SubmissionMode's docstring -- KOMPRIMIERT is the only mode this
    # project actually drives today. cover_sheet_generated_at is set the
    # first time the PDF is downloaded (informational only, re-downloading
    # doesn't clear it); cover_sheet_mailed_at is the taxpayer's own
    # self-attestation that they printed, signed, and mailed it -- we have
    # no way to verify this against the Finanzamt, so treat it as a UI
    # checklist item, not a legal confirmation.
    submission_mode: Mapped[SubmissionMode] = mapped_column(
        pg_enum(SubmissionMode, "submission_mode_enum"),
        nullable=False,
        default=SubmissionMode.KOMPRIMIERT,
        server_default="KOMPRIMIERT",
    )
    cover_sheet_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cover_sheet_mailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    user: Mapped["User"] = relationship(back_populates="tax_filings")
