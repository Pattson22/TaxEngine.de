"""
Progressive income tax calculation — §32a EStG (Einkommensteuertarif).

*** PLACEHOLDER / NOT CERTIFIED ***
This module reproduces the *structure* of the German progressive tax
formula for a single (unmarried, individually-assessed) taxpayer using the
2024 published coefficients. It is provided as an engineering scaffold so
the rest of the platform (refund estimates, UI previews) has a realistic
number to work with — it is explicitly NOT a certified tax calculation and
must not be used to generate the figures actually transmitted to ELSTER.
Any production submission path must run the official calculation via the
ERiC library (see docs/ELSTER_ERIC_INTEGRATION.md), which is the legally
authoritative source of truth.

The formula has five zones, each a polynomial in the taxable income (zvE),
using officially published coefficients that are recalibrated annually by
the Bundesministerium der Finanzen. Per §32a Abs. 1 Satz 6 EStG, the
resulting tax amount is rounded DOWN to the nearest full Euro.
"""

from __future__ import annotations

from decimal import ROUND_DOWN, Decimal

from app.tax_engine.constants import get_constants_for_year
from app.tax_engine.core import InvalidIncomeError

# Sanity ceiling: guards against garbage/overflow input reaching the tax
# formula (e.g. a unit-conversion bug passing euros where cents were
# expected). €100,000,000/year is far beyond any real individual filer and
# is rejected rather than silently "calculated".
_MAX_PLAUSIBLE_ZVE_CENTS = 100_000_000_00

# 2024 published §32a EStG coefficients (Bundesgesetzblatt).
# Zone 2 (Progressionszone 1): (a * y + b) * y
_ZONE2_A = Decimal("922.98")
_ZONE2_B = Decimal("1400.00")
# Zone 3 (Progressionszone 2): (a * z + b) * z + c
_ZONE3_A = Decimal("181.19")
_ZONE3_B = Decimal("2397.00")
_ZONE3_C = Decimal("1025.38")
# Zone 4 (linear 42% zone): rate * zvE - offset
_ZONE4_RATE = Decimal("0.42")
_ZONE4_OFFSET = Decimal("10602.13")
# Zone 5 (linear 45% "Reichensteuer" zone): rate * zvE - offset
_ZONE5_RATE = Decimal("0.45")
_ZONE5_OFFSET = Decimal("18936.88")

_CENTS_PER_EURO = Decimal("100")
_TEN_THOUSAND = Decimal("10000")


def _cents_to_euro(amount_cents: int) -> Decimal:
    return Decimal(amount_cents) / _CENTS_PER_EURO


def calculate_income_tax(zve_cents: int, tax_year: int = 2024) -> int:
    """Compute the annual income tax (Einkommensteuer) owed on a taxable
    income, using the standard/single-assessment §32a EStG tariff.

    Args:
        zve_cents: zu versteuerndes Einkommen in cents (output of
            `core.calculate_taxable_income`). Must be >= 0.
        tax_year: which year's bracket coefficients to apply. Only years
            present in `constants.SUPPORTED_TAX_YEARS` are accepted.

    Returns:
        Income tax owed, in cents, rounded down to the nearest full Euro
        per §32a Abs. 1 Satz 6 EStG (i.e. always a multiple of 100 cents).

    Raises:
        InvalidIncomeError: if zve_cents is negative or implausibly large.
        ValueError: if tax_year has no reviewed constants (see constants.py).
    """
    if zve_cents < 0:
        raise InvalidIncomeError("zve_cents cannot be negative.")
    if zve_cents > _MAX_PLAUSIBLE_ZVE_CENTS:
        raise InvalidIncomeError(
            f"zve_cents={zve_cents} exceeds the plausibility ceiling "
            f"({_MAX_PLAUSIBLE_ZVE_CENTS} cents). Refusing to calculate — "
            "likely a unit-conversion or upstream data error."
        )

    constants = get_constants_for_year(tax_year)
    zve_euro = _cents_to_euro(zve_cents)

    if zve_cents <= constants.grundfreibetrag_cents:
        # Zone 1: below the Grundfreibetrag, no tax is owed at all.
        tax_euro = Decimal("0")

    elif zve_cents <= constants.bracket_2_threshold_cents:
        # Zone 2: first progression zone.
        y = (zve_euro - _cents_to_euro(constants.grundfreibetrag_cents)) / _TEN_THOUSAND
        tax_euro = (_ZONE2_A * y + _ZONE2_B) * y

    elif zve_cents <= constants.bracket_3_threshold_cents:
        # Zone 3: second progression zone.
        z = (zve_euro - _cents_to_euro(constants.bracket_2_threshold_cents)) / _TEN_THOUSAND
        tax_euro = (_ZONE3_A * z + _ZONE3_B) * z + _ZONE3_C

    elif zve_cents <= constants.bracket_4_threshold_cents:
        # Zone 4: linear 42% zone.
        tax_euro = _ZONE4_RATE * zve_euro - _ZONE4_OFFSET

    else:
        # Zone 5: linear 45% "Reichensteuer" zone (top marginal rate).
        tax_euro = _ZONE5_RATE * zve_euro - _ZONE5_OFFSET

    # Statutory rounding: DOWN to the nearest full Euro, never up — this
    # favors the taxpayer by the smallest possible margin, matching §32a
    # Abs. 1 Satz 6 EStG.
    tax_euro_rounded = tax_euro.quantize(Decimal("1"), rounding=ROUND_DOWN)
    tax_cents = int(tax_euro_rounded * _CENTS_PER_EURO)

    # Defensive floor: the polynomial zones are continuous and non-negative
    # by construction at their boundaries, but guard against a future
    # coefficient typo producing a negative result.
    return max(tax_cents, 0)


def calculate_income_tax_for_assessment(
    zve_cents: int,
    tax_year: int = 2024,
    is_joint_assessment: bool = False,
) -> int:
    """Compute income tax under either the Grundtarif (single) or the
    Splittingverfahren (joint assessment / Zusammenveranlagung, §26, §32a
    Abs. 5 EStG).

    The Splittingverfahren halves the COMBINED taxable income of both
    spouses, runs that half through the standard single-taxpayer tariff,
    then doubles the result. This is mathematically independent of how the
    income is actually distributed between the two spouses — a
    Zusammenveranlagung with one spouse earning everything produces exactly
    the same tax as one where the income is split 50/50 — which is the
    entire point of the mechanism (it neutralizes the progressive rate's
    penalty on unequal-earning couples).

    Args:
        zve_cents: the COUPLE'S COMBINED zu versteuerndes Einkommen when
            is_joint_assessment=True, or a single taxpayer's zvE otherwise.
        tax_year: which year's tariff to apply.
        is_joint_assessment: mirrors `users.is_joint_assessment` in the DB
            schema.

    Returns:
        Income tax owed, in cents, rounded down to the nearest full Euro
        (the doubling of an already-rounded half-tax is itself always a
        whole-Euro amount).
    """
    if not is_joint_assessment:
        return calculate_income_tax(zve_cents, tax_year)

    # Integer floor division drops at most 1 cent, which cannot move the
    # final whole-Euro-rounded result — immaterial to the statutory outcome.
    half_zve_cents = zve_cents // 2
    tax_on_half = calculate_income_tax(half_zve_cents, tax_year)
    return tax_on_half * 2
