"""
Orchestrates one document upload: validate -> store. Mirrors
`app/eric/submission_service.py`'s role for the ELSTER scaffold -- the
one place the upload bytes and DocumentStorage meet, so storage.py stays
free of upload-handling concerns.

This project does NOT read/parse uploaded documents (no OCR, no AI
document understanding) -- a filer's Lohnsteuerbescheinigung is attached
purely as a reference link for their own records, the same way ELSTER's
own RABE mechanism (Referenzierung auf Belege) works: the software vendor
hosts the document and it's referenced by a link, never embedded or
parsed. The filer types the certificate's figures into the form
themselves; nothing here ever prefills it.
"""

from __future__ import annotations

import uuid

from app.documents.storage import DocumentStorage

MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB

SUPPORTED_UPLOAD_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class DocumentUploadError(Exception):
    """Raised when an uploaded file fails validation or storage."""


def upload_wage_certificate_document(
    *,
    user_id: uuid.UUID,
    filename: str,
    content_type: str,
    data: bytes,
    storage: DocumentStorage,
) -> str:
    """Validates and stores one uploaded Lohnsteuerbescheinigung, purely
    for the filer's own reference -- no content is read or parsed.

    Returns the storage key, to be attached to the WageTaxCertificate the
    filer ultimately saves (`source_document_url`) -- nothing here writes
    to the database itself.
    """
    if content_type not in SUPPORTED_UPLOAD_CONTENT_TYPES:
        raise DocumentUploadError(
            f"Unsupported file type ({content_type}). Upload a PDF, PNG, JPEG, or Word document."
        )
    if len(data) > MAX_UPLOAD_BYTES:
        raise DocumentUploadError("That file is too large (max 15 MB).")
    if len(data) == 0:
        raise DocumentUploadError("That file is empty.")

    safe_filename = filename.replace("/", "_").replace("\\", "_")
    storage_key = f"wage-tax-certificates/{user_id}/{uuid.uuid4()}-{safe_filename}"
    storage.upload(storage_key, data, content_type)
    return storage_key
