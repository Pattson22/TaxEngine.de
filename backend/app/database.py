"""
SQLAlchemy engine/session setup.

The models in `app/models/` describe the tables that `db/schema.sql`
already creates via raw DDL — `db/schema.sql` is the authoritative source
of truth for the schema (enum types, CHECK constraints, triggers), not
`Base.metadata.create_all()`. The models exist for the ORM's read/write
convenience, not to generate the schema. Keeping schema.sql authoritative
means constraints Alembic/SQLAlchemy can't express cleanly (CHECK clauses,
the updated_at trigger) still exist and are enforced at the DB layer.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a request-scoped DB session and always
    closes it, even if the request handler raises."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
