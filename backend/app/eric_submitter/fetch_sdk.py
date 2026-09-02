"""Fetches the real ERiC SDK from object storage and extracts it to
ERIC_SDK_PATH, run once at container startup before the worker itself
(see Dockerfile.worker's CMD).

Why this exists instead of baking the SDK into the image at build time:
`railway up`'s upload step only sends git-tracked content to Railway's
build daemon -- a gitignored local directory (backend/eric-sdk-linux/,
which a `COPY eric-sdk-linux /eric-sdk` step in the Dockerfile depended
on) is silently never uploaded, so that COPY step fails with "not found"
on Railway specifically, despite building fine with a local `docker
build` (which reads the real local filesystem, not a git-aware upload).
Confirmed by the actual failed build log:
"failed to calculate checksum of ref ...: /eric-sdk-linux: not found".

Fetching from S3 at container startup sidesteps this entirely -- reuses
the same S3-compatible storage (and Settings.s3_* config) already used
for document uploads, just a different bucket key
(ERIC_SDK_S3_KEY, default 'vendor/eric-sdk-linux.tar.gz'), uploaded once
by hand via `railway bucket credentials` + boto3, not through git or
`railway up` at all.
"""

from __future__ import annotations

import logging
import os
import tarfile
from pathlib import Path

import boto3

from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_SDK_S3_KEY = "vendor/eric-sdk-linux.tar.gz"


def fetch_and_extract_sdk(dest_path: str | Path) -> None:
    """Downloads the ERiC SDK tarball from S3 and extracts it to
    `dest_path`. Idempotent-ish: always re-fetches on every container
    start (no persistent volume), which is fine -- the container's own
    filesystem is ephemeral anyway."""
    dest = Path(dest_path)
    dest.mkdir(parents=True, exist_ok=True)

    key = os.environ.get("ERIC_SDK_S3_KEY", DEFAULT_SDK_S3_KEY)
    logger.info("Fetching ERiC SDK from s3://%s/%s", settings.s3_bucket_name, key)

    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name=settings.s3_region,
    )

    archive_path = dest / "_eric-sdk-linux.tar.gz"
    client.download_file(settings.s3_bucket_name, key, str(archive_path))

    with tarfile.open(archive_path) as tar:
        tar.extractall(dest)
    archive_path.unlink()

    logger.info("ERiC SDK extracted to %s", dest)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetch_and_extract_sdk(os.environ["ERIC_SDK_PATH"])
