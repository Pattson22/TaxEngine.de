"""
Python enums mirroring the PostgreSQL enum types in db/schema.sql
(`federal_state_enum`, `church_tax_type_enum`). Keeping these as a real
Enum rather than passing raw strings around means a typo in a state name
fails fast at the call site instead of silently producing a 9%-instead-of-8%
Kirchensteuer calculation.

If you add/rename a value here, update db/schema.sql's matching CREATE TYPE
in the same change — the two are meant to stay byte-for-byte in sync.
"""

from __future__ import annotations

from enum import Enum


class FederalState(str, Enum):
    BADEN_WUERTTEMBERG = "BADEN_WUERTTEMBERG"
    BAYERN = "BAYERN"
    BERLIN = "BERLIN"
    BRANDENBURG = "BRANDENBURG"
    BREMEN = "BREMEN"
    HAMBURG = "HAMBURG"
    HESSEN = "HESSEN"
    MECKLENBURG_VORPOMMERN = "MECKLENBURG_VORPOMMERN"
    NIEDERSACHSEN = "NIEDERSACHSEN"
    NORDRHEIN_WESTFALEN = "NORDRHEIN_WESTFALEN"
    RHEINLAND_PFALZ = "RHEINLAND_PFALZ"
    SAARLAND = "SAARLAND"
    SACHSEN = "SACHSEN"
    SACHSEN_ANHALT = "SACHSEN_ANHALT"
    SCHLESWIG_HOLSTEIN = "SCHLESWIG_HOLSTEIN"
    THUERINGEN = "THUERINGEN"


# The only two Bundesländer that levy the reduced 8% Kirchensteuer rate;
# all others levy 9% (see church_tax.py).
LOW_CHURCH_TAX_RATE_STATES = frozenset({FederalState.BAYERN, FederalState.BADEN_WUERTTEMBERG})


class ChurchTaxType(str, Enum):
    NONE = "NONE"
    ROEMISCH_KATHOLISCH = "ROEMISCH_KATHOLISCH"
    EVANGELISCH = "EVANGELISCH"
    OTHER = "OTHER"
