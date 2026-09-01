"""
DocumentStorage -- the abstraction boundary between our code and the
actual object-storage backend. `upload_service.py` depends only on
this interface. Unlike `app/eric/client.py`'s StubEricClient/
NativeEricClient split, there's only one implementation here: object
storage needs just account credentials, not a government developer
certificate, so there's no reason to fake it.

S3DocumentStorage works unmodified against AWS S3, Cloudflare R2, Railway
buckets, MinIO, or any other S3-API-compatible endpoint -- only
`app.config.settings`'s endpoint/credentials change between them, never
this code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings


class DocumentStorageError(Exception):
    """Raised when storing an uploaded document fails."""


class DocumentStorage(ABC):
    @abstractmethod
    def upload(self, key: str, data: bytes, content_type: str) -> None:
        """Uploads `data` under `key`. Raises DocumentStorageError on failure."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Deletes the object at `key`. Used by app/retention/purge_expired_data.py
        so an expired WageTaxCertificate's underlying file doesn't outlive its
        database row -- silently succeeds if the key is already gone (S3's
        delete_object is idempotent), never raises for a missing object."""


class S3DocumentStorage(DocumentStorage):
    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name=settings.s3_region,
        )
        self._bucket = settings.s3_bucket_name

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        try:
            self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)
        except (BotoCoreError, ClientError) as exc:
            raise DocumentStorageError(f"Couldn't store the uploaded document: {exc}") from exc

    def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except (BotoCoreError, ClientError) as exc:
            raise DocumentStorageError(f"Couldn't delete the stored document: {exc}") from exc
