"""
Solidaritätszuschlag (solidarity surcharge) — SolZG 1995 (as amended by the
2021 Freigrenze reform).

Levied as a percentage of the ASSESSED INCOME TAX (the output of
tax_brackets.calculate_income_tax[_for_assessment]), not of taxable income
directly. Since the 2021 reform roughly quintupled the exemption threshold
(Freigrenze), the large majority of low- and middle-income taxpayers now owe
no Soli at all — only upper-middle and high earners are affected.

Three zones (§4 SolZG):
    1. Income tax <= Freigrenze: no Soli.
    2. Milderungszone (tapering zone): Soli is capped at 11.9% of the
       amount by which income tax exceeds the Freigrenze — this keeps the
       transition into paying Soli gradual rather than an abrupt jump to
       the full 5.5%.
    3. Once 11.9% of the excess would exceed the flat 5.5% of the full
       income tax amount, the flat 5.5% rate applies from then on.

The zone boundary is implicit in the `min()` below — there is no separate
threshold constant to maintain, the two formulas simply cross over.
"""

from __future__ import annotations

from decimal import ROUND_DOWN, Decimal

from app.tax_engine.constants import get_constants_for_year
from app.tax_engine.core import InvalidIncomeError

_CENTS_PER_EURO = Decimal("100")


def calculate_solidaritaetszuschlag(
    income_tax_cents: int,
    is_joint_assessment: bool = False,
    tax_year: int = 2024,
) -> int:
    """Compute the Solidaritätszuschlag owed on top of assessed income tax.

    Args:
        income_tax_cents: the assessed income tax (output of
            tax_brackets.calculate_income_tax_for_assessment), in cents.
        is_joint_assessment: mirrors `users.is_joint_assessment` — joint
            filers get double the Freigrenze of single filers.
        tax_year: which year's Freigrenze/rates to apply.

    Returns:
        Solidaritätszuschlag owed, in cents, rounded down to the nearest
        full Euro (consistent with how the underlying income tax itself is
        rounded).

    Raises:
        InvalidIncomeError: if income_tax_cents is negative.
    """
    if income_tax_cents < 0:
        raise InvalidIncomeError("income_tax_cents cannot be negative.")

    constants = get_constants_for_year(tax_year)
    freigrenze_cents = (
        constants.soli_freigrenze_joint_cents
        if is_joint_assessment
        else constants.soli_freigrenze_single_cents
    )

    if income_tax_cents <= freigrenze_cents:
        return 0

    income_tax_euro = Decimal(income_tax_cents) / _CENTS_PER_EURO
    freigrenze_euro = Decimal(freigrenze_cents) / _CENTS_PER_EURO

    flat_amount_euro = constants.soli_rate * income_tax_euro
    tapered_amount_euro = constants.soli_milderungszone_rate * (income_tax_euro - freigrenze_euro)

    soli_euro = min(flat_amount_euro, tapered_amount_euro)
    soli_euro_rounded = soli_euro.quantize(Decimal("1"), rounding=ROUND_DOWN)

    return max(int(soli_euro_rounded) * 100, 0)


def calculate_solidaritaetszuschlag_on_capital_gains_tax(
    kapitalertragsteuer_cents: int,
    tax_year: int = 2024,
) -> int:
    """Compute Soli on Kapitalertragsteuer (capital gains withholding tax)
    — a FLAT 5.5%, with NO Freigrenze/Milderungszone at all.

    The exemption threshold implemented in `calculate_solidaritaetszuschlag`
    above only applies to the assessed (veranlagte) income tax under the
    progressive §32a tariff. Capital gains are taxed under the entirely
    separate flat Abgeltungsteuer regime (§32d EStG), and Soli on that
    withholding tax has no exemption threshold — it is 5.5% of whatever
    Kapitalertragsteuer was withheld, from the first cent. Using the
    regular-income-tax function here would incorrectly zero out Soli on
    small capital gains.

    Args:
        kapitalertragsteuer_cents: output of
            capital_gains.calculate_kapitalertragsteuer, in cents.
        tax_year: which year's Soli rate to apply.

    Returns:
        Soli owed on the capital gains tax, in cents, rounded down to the
        nearest full Euro.

    Raises:
        InvalidIncomeError: if kapitalertragsteuer_cents is negative.
    """
    if kapitalertragsteuer_cents < 0:
        raise InvalidIncomeError("kapitalertragsteuer_cents cannot be negative.")

    constants = get_constants_for_year(tax_year)
    tax_euro = Decimal(kapitalertragsteuer_cents) / _CENTS_PER_EURO
    soli_euro = (tax_euro * constants.soli_rate).quantize(Decimal("1"), rounding=ROUND_DOWN)

    return max(int(soli_euro) * 100, 0)
