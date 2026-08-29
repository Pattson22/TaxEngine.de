"""
Password hashing and JWT session tokens.

Password hashing uses argon2id (via argon2-cffi) rather than bcrypt —
argon2id is the current OWASP-recommended default and has no 72-byte input
truncation footgun. Never store or log a plaintext password anywhere,
including in exception messages.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from app.config import settings

_password_hasher = PasswordHasher()


def hash_password(plain_password: str) -> str:
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, plain_password)
    except VerifyMismatchError:
        return False


def create_access_token(user_id: UUID) -> str:
    expire_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire_at}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> UUID | None:
    """Returns the user ID encoded in a valid, unexpired token, or None if
    the token is invalid/expired/malformed. Never raises — callers treat a
    None return as "unauthenticated"."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None
