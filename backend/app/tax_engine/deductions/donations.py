"""
Spenden (donations) — §10b Abs. 1 EStG.

Donations and membership dues to recognized charitable, religious, or
political organizations are deductible as Sonderausgaben, capped at 20% of
the taxpayer's Gesamtbetrag der Einkünfte (total income across all income
categories, before Sonderausgaben deductions are applied).

Amounts above the cap are not lost under German law — they may be carried
forward to future tax years (Spendenvortrag, §10b Abs. 1 Satz 9 EStG),
indefinitely, with no expiry. `calculate_spenden_deduction_with_carryforward`
below computes one year's slice of that carry-forward chain; the persisted
running balance itself lives on `tax_filings.donation_carryforward_out_cents`
(this year's leftover becomes next year's `..._in_cents` — see
app/services/tax_calculation_service.py for how consecutive years are
chained together by looking up the prior year's filing row).
"""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class SpendenvortragResult:
    """One year's slice of the donation carry-forward chain."""

    deductible_this_year_cents: int
    carryforward_out_cents: int


def calculate_spenden_deduction_with_carryforward(
    amount_donated_this_year_cents: int,
    carryforward_in_cents: int,
    gesamtbetrag_der_einkuenfte_cents: int,
    tax_year: int = 2024,
) -> SpendenvortragResult:
    """Compute this year's deductible donation amount INCLUDING any unused
    carry-forward from prior years, and how much (if any) newly carries
    forward to next year.

    This year's newly-donated amount and the incoming carry-forward are
    pooled together and treated identically against the 20% cap — German
    law does not require the carried-forward amount to be used first or
    last, it's simply a combined pool (§10b Abs. 1 Satz 9 EStG).

    Args:
        amount_donated_this_year_cents: NEW documented donations made
            during this tax year (not including any carry-forward).
        carryforward_in_cents: unused donation deduction carried in from
            the prior year's `SpendenvortragResult.carryforward_out_cents`
            (0 if there is no prior year or nothing was carried).
        gesamtbetrag_der_einkuenfte_cents: this year's total income across
            all income categories.
        tax_year: which year's cap percentage to apply.

    Returns:
        A SpendenvortragResult with this year's deductible amount and the
        leftover to carry into next year.

    Raises:
        DeductionValidationError: on negative inputs.
    """
    if amount_donated_this_year_cents < 0:
        raise DeductionValidationError("amount_donated_this_year_cents cannot be negative.")
    if carryforward_in_cents < 0:
        raise DeductionValidationError("carryforward_in_cents cannot be negative.")
    if gesamtbetrag_der_einkuenfte_cents < 0:
        raise DeductionValidationError("gesamtbetrag_der_einkuenfte_cents cannot be negative.")

    total_available_cents = amount_donated_this_year_cents + carryforward_in_cents
    if total_available_cents == 0:
        return SpendenvortragResult(deductible_this_year_cents=0, carryforward_out_cents=0)

    constants = get_constants_for_year(tax_year)
    cap_euro = (
        Decimal(gesamtbetrag_der_einkuenfte_cents) / _CENTS_PER_EURO
    ) * constants.spenden_deduction_cap_percentage
    cap_cents = int(cap_euro.quantize(Decimal("1"), rounding=ROUND_DOWN)) * 100

    deductible_this_year_cents = min(total_available_cents, cap_cents)
    carryforward_out_cents = total_available_cents - deductible_this_year_cents

    return SpendenvortragResult(deductible_this_year_cents, carryforward_out_cents)
