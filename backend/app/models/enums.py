"""
Python enums mirroring the remaining PostgreSQL enum types in
db/schema.sql that `tax_engine` itself has no need to know about
(TaxClass, DeductionCategory, FilingStatus).

`FederalState` and `ChurchTaxType` are NOT redefined here — they already
exist in `app.tax_engine.enums` because the calculation engine needs them
directly (church_tax.py, soli.py). Re-exporting them from here means model
code only ever imports from `app.models.enums`, without callers needing to
know which enums originated in the calculation core vs. the persistence
layer.
"""

from __future__ import annotations

from enum import Enum
from typing import TypeVar

from sqlalchemy import Enum as PgEnum

from app.tax_engine.enums import ChurchTaxType, FederalState

__all__ = [
    "ChurchTaxType",
    "DeductionCategory",
    "FederalState",
    "FilingStatus",
    "SubmissionMode",
    "TaxClass",
    "pg_enum",
]

_EnumT = TypeVar("_EnumT", bound=Enum)


def pg_enum(enum_cls: type[_EnumT], name: str) -> PgEnum:
    """Build a SQLAlchemy column type bound to an ALREADY-EXISTING Postgres
    enum type (created by db/schema.sql), storing each member's `.value`
    rather than its Python attribute name.

    `create_type=False` is essential: without it, SQLAlchemy attempts to
    `CREATE TYPE` on `Base.metadata.create_all()`, which would collide with
    (or silently diverge from) the type schema.sql already created. This
    module never calls create_all() in application code for exactly that
    reason — schema.sql stays the single source of truth for DDL.
    """
    return PgEnum(
        enum_cls,
        name=name,
        create_type=False,
        values_callable=lambda cls: [member.value for member in cls],
    )


class TaxClass(str, Enum):
    I = "I"
    II = "II"
    III = "III"
    IV = "IV"
    V = "V"
    VI = "VI"


class DeductionCategory(str, Enum):
    COMMUTE = "COMMUTE"
    HOME_OFFICE = "HOME_OFFICE"
    WORK_EQUIPMENT = "WORK_EQUIPMENT"
    FURTHER_EDUCATION = "FURTHER_EDUCATION"
    DOUBLE_HOUSEHOLD = "DOUBLE_HOUSEHOLD"
    INSURANCE = "INSURANCE"
    DONATIONS = "DONATIONS"
    CHILDCARE = "CHILDCARE"
    HANDWERKERLEISTUNGEN = "HANDWERKERLEISTUNGEN"
    OTHER = "OTHER"


class FilingStatus(str, Enum):
    DRAFT = "DRAFT"
    CALCULATED = "CALCULATED"
    FEE_PAID = "FEE_PAID"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class SubmissionMode(str, Enum):
    """Which ELSTER transmission path a filing uses.

    KOMPRIMIERT ("compressed"/unauthenticated): the XML is transmitted to
    the Finanzamt via ERiC same as any other submission, but without a
    personal ELSTER certificate attached, so it isn't legally binding on
    its own -- the taxpayer must additionally print, sign, and mail a
    cover sheet (see app/eric/cover_sheet.py) to complete the filing. This
    is the only mode this project supports right now, since it doesn't
    require every user to first enroll their own ELSTER certificate.

    AUTHENTIFIZIERT: the fully paperless path, authenticated with the
    taxpayer's own personal ELSTER certificate (obtained by them directly
    from ElsterOnline, independent of us). Not implemented yet -- reserved
    so the column doesn't need a second migration once it is.
    """

    KOMPRIMIERT = "KOMPRIMIERT"
    AUTHENTIFIZIERT = "AUTHENTIFIZIERT"
