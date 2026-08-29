"""
Unit tests for app/documents/. extraction_service.py's validation/routing
logic is tested with mocked DocumentStorage/DocumentExtractionClient (same
pattern as test_eric.py's submission_service tests) since it doesn't need
real infra to prove its own logic. S3DocumentStorage is tested against a
real local MinIO container (matching this project's DB tests, which run
against a real Dockerized Postgres rather than mocking SQLAlchemy) --
skipped automatically if MinIO isn't reachable. AnthropicDocumentExtractionClient
is tested with a mocked anthropic.Anthropic client, since a real call needs
a real API key this project doesn't have configured yet (see
app/config.py's placeholder).
"""

from __future__ import annotations

import io
from unittest.mock import MagicMock

import anthropic
import docx
import pytest
from botocore.exceptions import ClientError

from app.documents.extraction_client import (
    AnthropicDocumentExtractionClient,
    DocumentExtractionError,
    _build_content_block,
)
from app.documents.extraction_service import (
    MAX_UPLOAD_BYTES,
    extract_wage_certificate_from_upload,
)
from app.documents.storage import DocumentStorageError, S3DocumentStorage
from app.schemas.document_extraction import WageCertificateExtraction


def _make_docx_bytes(paragraphs: list[str]) -> bytes:
    document = docx.Document()
    for text in paragraphs:
        document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


class TestExtractionService:
    def test_rejects_unsupported_content_type(self):
        with pytest.raises(DocumentExtractionError, match="Unsupported file type"):
            extract_wage_certificate_from_upload(
                user_id=__import__("uuid").uuid4(),
                filename="notes.txt",
                content_type="text/plain",
                data=b"hello",
                storage=MagicMock(),
                extraction_client=MagicMock(),
            )

    def test_rejects_oversized_file(self):
        with pytest.raises(DocumentExtractionError, match="too large"):
            extract_wage_certificate_from_upload(
                user_id=__import__("uuid").uuid4(),
                filename="big.pdf",
                content_type="application/pdf",
                data=b"x" * (MAX_UPLOAD_BYTES + 1),
                storage=MagicMock(),
                extraction_client=MagicMock(),
            )

    def test_rejects_empty_file(self):
        with pytest.raises(DocumentExtractionError, match="empty"):
            extract_wage_certificate_from_upload(
                user_id=__import__("uuid").uuid4(),
                filename="empty.pdf",
                content_type="application/pdf",
                data=b"",
                storage=MagicMock(),
                extraction_client=MagicMock(),
            )

    def test_uploads_original_bytes_and_calls_extraction_for_pdf(self):
        storage = MagicMock()
        extraction_client = MagicMock()
        extraction_client.extract_wage_certificate.return_value = WageCertificateExtraction(
            employer_name="Muster GmbH", gross_wage_cents=4500000
        )
        user_id = __import__("uuid").uuid4()

        result, storage_key = extract_wage_certificate_from_upload(
            user_id=user_id,
            filename="lohn.pdf",
            content_type="application/pdf",
            data=b"%PDF-1.4 fake pdf bytes",
            storage=storage,
            extraction_client=extraction_client,
        )

        storage.upload.assert_called_once()
        called_key, called_data, called_content_type = storage.upload.call_args[0]
        assert str(user_id) in called_key
        assert called_key.endswith("-lohn.pdf")
        assert called_data == b"%PDF-1.4 fake pdf bytes"
        assert called_content_type == "application/pdf"

        extraction_client.extract_wage_certificate.assert_called_once_with(
            b"%PDF-1.4 fake pdf bytes", "application/pdf"
        )
        assert result.employer_name == "Muster GmbH"
        assert storage_key == called_key

    def test_converts_docx_to_text_before_extraction(self):
        storage = MagicMock()
        extraction_client = MagicMock()
        extraction_client.extract_wage_certificate.return_value = WageCertificateExtraction()
        docx_bytes = _make_docx_bytes(["Lohnsteuerbescheinigung 2024", "Muster GmbH", "45.000,00 EUR"])

        extract_wage_certificate_from_upload(
            user_id=__import__("uuid").uuid4(),
            filename="lohn.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            data=docx_bytes,
            storage=storage,
            extraction_client=extraction_client,
        )

        extraction_client.extract_wage_certificate.assert_called_once()
        called_data, called_media_type = extraction_client.extract_wage_certificate.call_args[0]
        assert called_media_type == "text/plain"
        text = called_data.decode("utf-8")
        assert "Muster GmbH" in text
        assert "45.000,00 EUR" in text

    def test_rejects_corrupt_docx(self):
        with pytest.raises(DocumentExtractionError, match="Word document"):
            extract_wage_certificate_from_upload(
                user_id=__import__("uuid").uuid4(),
                filename="broken.docx",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                data=b"not a real docx file",
                storage=MagicMock(),
                extraction_client=MagicMock(),
            )


class TestBuildContentBlock:
    def test_pdf_becomes_a_document_block(self):
        block = _build_content_block(b"pdf-bytes", "application/pdf")
        assert block["type"] == "document"
        assert block["source"]["media_type"] == "application/pdf"

    def test_image_becomes_an_image_block(self):
        block = _build_content_block(b"png-bytes", "image/png")
        assert block["type"] == "image"

    def test_text_plain_becomes_a_text_block(self):
        block = _build_content_block("hello".encode(), "text/plain")
        assert block == {"type": "text", "text": "hello"}

    def test_unsupported_media_type_raises(self):
        with pytest.raises(DocumentExtractionError, match="Unsupported"):
            _build_content_block(b"data", "application/zip")


class TestAnthropicDocumentExtractionClient:
    def _client_with_mocked_sdk(self, mock_response) -> AnthropicDocumentExtractionClient:
        client = AnthropicDocumentExtractionClient()
        client._client = MagicMock()
        client._client.messages.create.return_value = mock_response
        return client

    def test_parses_tool_use_response_into_extraction(self):
        tool_use_block = MagicMock()
        tool_use_block.type = "tool_use"
        tool_use_block.input = {
            "employer_name": "Muster GmbH",
            "gross_wage_cents": 4500000,
            "income_tax_withheld_cents": 900000,
            "solidarity_surcharge_cents": 0,
            "church_tax_withheld_cents": 0,
            "warnings": [],
        }
        response = MagicMock()
        response.content = [tool_use_block]
        client = self._client_with_mocked_sdk(response)

        result = client.extract_wage_certificate(b"pdf-bytes", "application/pdf")

        assert result.employer_name == "Muster GmbH"
        assert result.gross_wage_cents == 4500000
        assert result.warnings == []

    def test_missing_tool_use_block_raises(self):
        text_block = MagicMock()
        text_block.type = "text"
        response = MagicMock()
        response.content = [text_block]
        client = self._client_with_mocked_sdk(response)

        with pytest.raises(DocumentExtractionError, match="no structured result"):
            client.extract_wage_certificate(b"pdf-bytes", "application/pdf")

    def test_api_connection_error_is_wrapped(self):
        client = AnthropicDocumentExtractionClient()
        client._client = MagicMock()
        client._client.messages.create.side_effect = anthropic.APIConnectionError(request=MagicMock())

        with pytest.raises(DocumentExtractionError, match="Couldn't reach"):
            client.extract_wage_certificate(b"pdf-bytes", "application/pdf")


@pytest.fixture
def minio_storage():
    storage = S3DocumentStorage.__new__(S3DocumentStorage)
    import boto3

    storage._client = boto3.client(
        "s3",
        endpoint_url="http://localhost:9000",
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin123",
        region_name="us-east-1",
    )
    storage._bucket = "taxengine-documents"
    try:
        storage._client.list_buckets()
    except Exception:
        pytest.skip("MinIO not reachable at localhost:9000 -- skipping real-storage test.")
    return storage


class TestS3DocumentStorage:
    def test_uploads_to_real_minio(self, minio_storage):
        key = "tests/test_document_extraction/roundtrip.txt"
        minio_storage.upload(key, b"hello from a test", "text/plain")

        fetched = minio_storage._client.get_object(Bucket=minio_storage._bucket, Key=key)
        assert fetched["Body"].read() == b"hello from a test"
        assert fetched["ContentType"] == "text/plain"

    def test_wraps_client_errors(self):
        storage = S3DocumentStorage.__new__(S3DocumentStorage)
        storage._client = MagicMock()
        storage._client.put_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "nope"}}, "PutObject"
        )
        storage._bucket = "does-not-exist"

        with pytest.raises(DocumentStorageError, match="Couldn't store"):
            storage.upload("some/key.pdf", b"data", "application/pdf")
