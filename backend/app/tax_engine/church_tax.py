"""
Kirchensteuer (church tax) — levied by the 16 Bundesländer's own church tax
laws (Landeskirchensteuergesetze), collected by the Finanzamt alongside
income tax on behalf of the registered religious body.

*** SIMPLIFIED / PLACEHOLDER — see caveats below ***
`calculate_kirchensteuer` implements the standard calculation: a flat
percentage (8% in Bayern/Baden-Württemberg, 9% elsewhere) of the assessed
income tax. `apply_kirchensteuer_kappung` layers Kappung (capping) on top
of that — see its own docstring for the state-by-state rate table and its
approximations. One real-world refinement remains explicitly OUT OF SCOPE:

  Kinderfreibetrag adjustment: the assessed-income-tax base used for
  Kirchensteuer (and Soli) purposes is technically computed WITH the
  Kinderfreibetrag applied even for taxpayers who came out ahead keeping
  Kindergeld instead for income tax purposes (a quirk of how the base is
  defined, §51a EStG / §3 SolZG). This module continues to use the
  actually-assessed (post-Günstigerprüfung) income tax as its base — see
  tax_engine/kinderfreibetrag.py's module docstring for the same caveat.
"""

from __future__ import annotations

from decimal import ROUND_DOWN, Decimal

from app.tax_engine.constants import get_constants_for_year
from app.tax_engine.core import InvalidIncomeError
from app.tax_engine.enums import LOW_CHURCH_TAX_RATE_STATES, ChurchTaxType, FederalState

_CENTS_PER_EURO = Decimal("100")


def calculate_kirchensteuer(
    income_tax_cents: int,
    church_tax_type: ChurchTaxType,
    residence_state: FederalState,
    tax_year: int = 2024,
) -> int:
    """Compute Kirchensteuer owed on top of assessed income tax.

    Args:
        income_tax_cents: the assessed income tax (output of
            tax_brackets.calculate_income_tax_for_assessment), in cents.
        church_tax_type: the taxpayer's registered church tax status.
            ChurchTaxType.NONE always yields 0 regardless of state/income.
        residence_state: determines the 8% vs. 9% rate.
        tax_year: which year's rates to apply.

    Returns:
        Kirchensteuer owed, in cents, rounded down to the nearest full Euro.

    Raises:
        InvalidIncomeError: if income_tax_cents is negative.
    """
    if income_tax_cents < 0:
        raise InvalidIncomeError("income_tax_cents cannot be negative.")

    if church_tax_type == ChurchTaxType.NONE:
        return 0

    constants = get_constants_for_year(tax_year)
    rate = (
        constants.church_tax_rate_bavaria_bw
        if residence_state in LOW_CHURCH_TAX_RATE_STATES
        else constants.church_tax_rate_other_states
    )

    income_tax_euro = Decimal(income_tax_cents) / _CENTS_PER_EURO
    church_tax_euro = (income_tax_euro * rate).quantize(Decimal("1"), rounding=ROUND_DOWN)

    return max(int(church_tax_euro) * 100, 0)


def calculate_kirchensteuer_kappung_cap(
    taxable_income_cents: int,
    residence_state: FederalState,
    tax_year: int = 2024,
) -> int | None:
    """Compute the Kappung ceiling (a percentage of TAXABLE INCOME, not
    income tax) for a given state, or None if that state offers no Kappung
    at all (Bayern) or isn't in the lookup table.

    See `constants.TaxYearConstants.kirchensteuer_kappung_rates` for the
    per-state rate table and its documented approximations (denomination-
    level differences and Antrag-vs-automatic distinctions are not
    modeled; the more conservative rate is used where a state publishes
    more than one).

    Raises:
        InvalidIncomeError: if taxable_income_cents is negative.
    """
    if taxable_income_cents < 0:
        raise InvalidIncomeError("taxable_income_cents cannot be negative.")

    constants = get_constants_for_year(tax_year)
    rate = constants.kirchensteuer_kappung_rates.get(residence_state)
    if rate is None:
        return None

    income_euro = Decimal(taxable_income_cents) / _CENTS_PER_EURO
    cap_euro = (income_euro * rate).quantize(Decimal("1"), rounding=ROUND_DOWN)
    return max(int(cap_euro) * 100, 0)


def apply_kirchensteuer_kappung(
    standard_kirchensteuer_cents: int,
    taxable_income_cents: int,
    residence_state: FederalState,
    tax_year: int = 2024,
) -> int:
    """Cap Kirchensteuer at the state's Kappungssatz, if that ceiling is
    lower than the standard percentage-of-income-tax amount.

    Args:
        standard_kirchensteuer_cents: output of calculate_kirchensteuer.
        taxable_income_cents: zu versteuerndes Einkommen — the base the
            Kappung percentage applies to (NOT income tax).
        residence_state: determines whether/which Kappungssatz applies.
        tax_year: which year's rates to apply.

    Returns:
        The lesser of the standard Kirchensteuer and the state's Kappung
        ceiling — or the standard amount unchanged if the state offers no
        Kappung.

    Raises:
        InvalidIncomeError: if either cents argument is negative.
    """
    if standard_kirchensteuer_cents < 0:
        raise InvalidIncomeError("standard_kirchensteuer_cents cannot be negative.")

    cap_cents = calculate_kirchensteuer_kappung_cap(taxable_income_cents, residence_state, tax_year)
    if cap_cents is None:
        return standard_kirchensteuer_cents

    return min(standard_kirchensteuer_cents, cap_cents)
