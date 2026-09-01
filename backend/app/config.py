"""
Application settings, loaded from environment variables (or a `.env` file
in local development). Never hard-code secrets here — this file defines
*where* configuration comes from, not the values themselves.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Postgres connection string. The `postgresql+psycopg://` driver prefix
    # selects psycopg3 (see requirements.txt) rather than the legacy
    # psycopg2 driver.
    database_url: str = "postgresql+psycopg://taxengine:taxengine@localhost:5432/taxengine"

    # JWT session tokens (python-jose). SECRET_KEY MUST be overridden via
    # environment variable in any non-local environment — this default
    # exists only so the app can boot for local development without a .env
    # file, and must never be used in production.
    jwt_secret_key: str = "insecure-development-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    cors_allowed_origins: list[str] = ["http://localhost:3000"]

    # Stripe (processing-fee payment). Both MUST be overridden via
    # environment variable in any non-local environment -- these
    # placeholders exist only so the app can boot without a .env file, and
    # any call against them will simply fail against the real Stripe API
    # (they are not valid keys), never silently succeed insecurely.
    stripe_secret_key: str = "sk_test_placeholder_override_in_env"
    stripe_webhook_secret: str = "whsec_placeholder_override_in_env"

    # S3-compatible object storage for uploaded documents. Works
    # unmodified against AWS S3, Cloudflare R2, Railway buckets, MinIO,
    # or any other S3-API-compatible provider -- only the endpoint/
    # credentials change between them, never the client code.
    s3_endpoint_url: str = "http://localhost:9000"
    s3_bucket_name: str = "taxengine-documents"
    s3_access_key_id: str = "placeholder_override_in_env"
    s3_secret_access_key: str = "placeholder_override_in_env"
    s3_region: str = "us-east-1"

    # Path to one platform's extracted ERiC SDK directory (the contents of
    # ERiC-<version>-<Platform>.jar, itself a zip -- see
    # app/eric/native_bindings.py and docs/ELSTER_ERIC_INTEGRATION.md).
    # Only read by NativeEricClient, which isn't wired into the FastAPI
    # app by default (ERiC must never load inside the web process --
    # ELSTER_ERIC_INTEGRATION.md section 2), so this stays unset/unused
    # for the app itself; a future eric-submitter worker reads it directly.
    eric_sdk_path: str | None = None

    # BZSt-issued software-manufacturer id, required by the real
    # TransferHeader schema (app/eric/xml_builder.py) -- this project
    # hasn't completed that separate registration step yet (see
    # docs/ELSTER_ERIC_INTEGRATION.md), so this placeholder exists only so
    # the app can boot; any real EricCheckXML()/EricBearbeiteVorgang()
    # call against it fails loudly with an invalid-Hersteller-ID error,
    # never silently succeeds.
    eric_hersteller_id: str = "00000_override_in_env_once_registered"

    environment: str = "development"

    # Error monitoring (Sentry). Empty by default -- sentry_sdk.init()
    # with a falsy dsn disables the SDK entirely (every capture call
    # becomes a no-op), so this is safe to leave unset in dev/test/CI.
    # See app/monitoring.py for why send_default_pii and
    # max_request_body_size are hard-pinned rather than configurable:
    # this app's request bodies routinely contain full tax/financial
    # data, which must never leave the process on an error event.
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.0


settings = Settings()
