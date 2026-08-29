from __future__ import annotations

from pydantic import BaseModel, Field


class WageCertificateExtraction(BaseModel):
    """What Claude read off an uploaded Lohnsteuerbescheinigung. Every
    monetary/identifying field is nullable -- a field Claude couldn't read
    confidently comes back None with an explanation in `warnings`, rather
    than a guessed value. This is a prefill for the existing add-employer
    form, never auto-saved -- the filer reviews and corrects it before any
    of these numbers become a real WageTaxCertificate row."""

    employer_name: str | None = None
    gross_wage_cents: int | None = None
    income_tax_withheld_cents: int | None = None
    solidarity_surcharge_cents: int | None = None
    church_tax_withheld_cents: int | None = None
    warnings: list[str] = Field(default_factory=list)


class WageCertificateExtractionResult(WageCertificateExtraction):
    """The extraction plus where the uploaded original was stored, so the
    filer's eventual WageTaxCertificateCreate can carry it forward in
    `source_document_url` for provenance."""

    source_document_url: str
