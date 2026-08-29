"""
DocumentExtractionClient -- the abstraction boundary between our code and
the actual Claude API call. `extraction_service.py` depends only on this
interface, never on the Anthropic SDK directly.

Real (not a stub) implementation, same reasoning as storage.py: reading a
document needs only an API key, not a BZSt-style certificate, so there's
nothing to fake here the way NativeEricClient has to be.
"""

from __future__ import annotations

import base64
from abc import ABC, abstractmethod

import anthropic

from app.config import settings
from app.schemas.document_extraction import WageCertificateExtraction

_MODEL = "claude-opus-5"

# strict:true requires every property in `required` -- optional fields are
# expressed as nullable types, not omitted from `required`.
_WAGE_CERTIFICATE_TOOL = {
    "name": "record_wage_certificate",
    "description": (
        "Records the fields read from a German Lohnsteuerbescheinigung "
        "(annual wage tax certificate). Use null for any field that isn't "
        "legible or present, and add an entry to `warnings` explaining why."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "employer_name": {"type": ["string", "null"]},
            "gross_wage_cents": {
                "type": ["integer", "null"],
                "description": "Bruttoarbeitslohn, in cents (e.g. 4500000 for 45.000,00 EUR).",
            },
            "income_tax_withheld_cents": {
                "type": ["integer", "null"],
                "description": "Einbehaltene Lohnsteuer, in cents.",
            },
            "solidarity_surcharge_cents": {
                "type": ["integer", "null"],
                "description": "Einbehaltener Solidaritaetszuschlag, in cents.",
            },
            "church_tax_withheld_cents": {
                "type": ["integer", "null"],
                "description": "Einbehaltene Kirchensteuer, in cents.",
            },
            "warnings": {
                "type": "array",
                "items": {"type": "string"},
                "description": "One entry per field that couldn't be read confidently, in plain English.",
            },
        },
        "required": [
            "employer_name",
            "gross_wage_cents",
            "income_tax_withheld_cents",
            "solidarity_surcharge_cents",
            "church_tax_withheld_cents",
            "warnings",
        ],
        "additionalProperties": False,
    },
    "strict": True,
}

_PROMPT = (
    "This is a German Lohnsteuerbescheinigung (annual wage tax certificate). "
    "Read it and call record_wage_certificate with the figures it reports. "
    "Monetary fields are in cents, not euros -- multiply the printed EUR "
    "amount by 100 (e.g. 45.000,00 EUR -> 4500000). If a figure is missing, "
    "illegible, or this document isn't a Lohnsteuerbescheinigung at all, "
    "leave that field null and say why in warnings."
)


class DocumentExtractionError(Exception):
    """Raised when a document can't be read at all -- a corrupt file, an
    unreachable API, an unsupported file type -- as opposed to a
    well-formed document with some fields it legitimately couldn't find
    (that's a `warnings` entry on the result, not an error)."""


class DocumentExtractionClient(ABC):
    @abstractmethod
    def extract_wage_certificate(self, data: bytes, media_type: str) -> WageCertificateExtraction:
        """`media_type` is one of application/pdf, image/png, image/jpeg,
        or text/plain (pre-extracted .docx text -- see extraction_service.py,
        which is where the docx -> text conversion happens; this client
        only ever sees a format Claude's document/image/text blocks accept
        natively)."""


class AnthropicDocumentExtractionClient(DocumentExtractionClient):
    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def extract_wage_certificate(self, data: bytes, media_type: str) -> WageCertificateExtraction:
        content_block = _build_content_block(data, media_type)
        try:
            response = self._client.messages.create(
                model=_MODEL,
                max_tokens=1024,
                output_config={"effort": "medium"},
                tools=[_WAGE_CERTIFICATE_TOOL],
                tool_choice={"type": "tool", "name": "record_wage_certificate"},
                messages=[
                    {
                        "role": "user",
                        "content": [content_block, {"type": "text", "text": _PROMPT}],
                    }
                ],
            )
        except anthropic.APIConnectionError as exc:
            raise DocumentExtractionError("Couldn't reach the document reader. Try again shortly.") from exc
        except anthropic.APIStatusError as exc:
            raise DocumentExtractionError(f"Couldn't read this document: {exc.message}") from exc

        tool_use = next((block for block in response.content if block.type == "tool_use"), None)
        if tool_use is None:
            raise DocumentExtractionError("Couldn't read this document: no structured result was returned.")

        return WageCertificateExtraction(**tool_use.input)


def _build_content_block(data: bytes, media_type: str) -> dict:
    if media_type == "text/plain":
        return {"type": "text", "text": data.decode("utf-8", errors="replace")}
    if media_type == "application/pdf":
        return {
            "type": "document",
            "source": {"type": "base64", "media_type": media_type, "data": base64.b64encode(data).decode()},
        }
    if media_type in ("image/png", "image/jpeg"):
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": base64.b64encode(data).decode()},
        }
    raise DocumentExtractionError(f"Unsupported file type: {media_type}")
