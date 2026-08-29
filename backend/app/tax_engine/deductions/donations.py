"""
Spenden (donations) — §10b Abs. 1 EStG.

Donations and membership dues to recognized charitable, religious, or
political organizations are deductible as Sonderausgaben, capped at 20% of
the taxpayer's Gesamtbetrag der Einkünfte (total income across all income
categories, before Sonderausgaben deductions are applied).

Amounts above the cap are not lost under German law — they may be carried
forward to future tax years (Spendenvortrag, §10b Abs. 1 Satz 9 EStG). That
carry-forward is intentionally OUT OF SCOPE here: it requires persisting a
running balance per user across tax years, which belongs in the API/DB
layer (a `spenden_carryforward_cents` column tracked per user), not in this
stateless per-year calculation function.
"""

from __future__ import annotations

from decimal import ROUND_DOWN, Decimal

from app.tax_engine.constants import get_constants_for_year
from app.tax_engine.deductions.errors import DeductionValidationError

_CENTS_PER_EURO = Decimal("100")


def calculate_spenden_deduction(
    amount_donated_cents: int,
    gesamtbetrag_der_einkuenfte_cents: int,
    tax_year: int = 2024,
) -> int:
    """Compute the deductible portion of donations made in the tax year.

    Args:
        amount_donated_cents: total documented donations/membership dues
            for the year.
        gesamtbetrag_der_einkuenfte_cents: the taxpayer's total income
            across all income categories for the year (for the MVP's
            employee-only scope, this is gross wage income; a future
            multi-income-category engine would sum across all categories
            here).
        tax_year: which year's cap percentage to apply.

    Returns:
        The deductible amount, in cents — the lesser of the amount donated
        and 20% of Gesamtbetrag der Einkünfte.

    Raises:
        DeductionValidationError: on negative inputs.
    """
    if amount_donated_cents < 0:
        raise DeductionValidationError("amount_donated_cents cannot be negative.")
    if gesamtbetrag_der_einkuenfte_cents < 0:
        raise DeductionValidationError("gesamtbetrag_der_einkuenfte_cents cannot be negative.")

    if amount_donated_cents == 0:
        return 0

    constants = get_constants_for_year(tax_year)
    cap_euro = (
        Decimal(gesamtbetrag_der_einkuenfte_cents) / _CENTS_PER_EURO
    ) * constants.spenden_deduction_cap_percentage
    cap_cents = int(cap_euro.quantize(Decimal("1"), rounding=ROUND_DOWN)) * 100

    return min(amount_donated_cents, cap_cents)
