from __future__ import annotations

from pydantic import BaseModel


class DocumentUploadResult(BaseModel):
    """Where an uploaded Lohnsteuerbescheinigung was stored, so the
    filer's eventual WageTaxCertificateCreate can carry it forward in
    `source_document_url` -- a reference link only, never parsed content."""

    source_document_url: str
