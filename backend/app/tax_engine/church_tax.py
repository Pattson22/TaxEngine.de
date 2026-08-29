"""
Kirchensteuer (church tax) — levied by the 16 Bundesländer's own church tax
laws (Landeskirchensteuergesetze), collected by the Finanzamt alongside
income tax on behalf of the registered religious body.

*** SIMPLIFIED / PLACEHOLDER — see caveats below ***
This module implements the common-case calculation: a flat percentage
(8% in Bayern/Baden-Württemberg, 9% elsewhere) of the assessed income tax,
for taxpayers who registered a church_tax_type other than NONE. Two
real-world refinements are explicitly OUT OF SCOPE for this MVP module and
would need to be added before this figure is transmitted to the Finanzamt:

  1. Kappung (capping): several states cap Kirchensteuer at 2.75%-4% of
     TAXABLE INCOME (not income tax) for high earners, if that produces a
     lower result than the percentage-of-income-tax calculation — this
     requires an explicit application (Kappungsantrag) in some states and
     is applied automatically in others.
  2. Kinderfreibetrag adjustment: the assessed-income-tax base used for
     Kirchensteuer purposes is technically computed WITH the
     Kinderfreibetrag applied even for taxpayers who received Kindergeld
     instead (a quirk of how the base is defined) — since this MVP does
     not yet model children/Kinderfreibetrag at all, that adjustment
     cannot yet be applied and the plain assessed income tax is used as-is.
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
