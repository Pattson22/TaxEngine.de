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

    environment: str = "development"


settings = Settings()
