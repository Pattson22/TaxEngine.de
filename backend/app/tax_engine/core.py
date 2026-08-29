"""
Core calculation primitives: Werbungskosten aggregation, Pauschbetrag
comparison, and zu versteuerndes Einkommen (zvE) derivation.

Money handling convention (applies to the whole `tax_engine` package):
    - All amounts are Python `int` CENTS. Never `float`.
    - Functions that could otherwise divide (e.g. averaging) must round using
      explicit, documented rounding — banker's rounding is avoided in favor
      of the tax-law-standard "round half up" via `decimal.ROUND_HALF_UP`
      where division is unavoidable (see tax_brackets.py).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.tax_engine.constants import get_constants_for_year


class TaxEngineError(Exception):
    """Base exception for all tax_engine domain errors."""


class InvalidIncomeError(TaxEngineError):
    """Raised when an income or deduction figure fails a sanity/legal bound check."""


@dataclass(frozen=True)
class DeductionLine:
    """A single Werbungskosten line item, already resolved to a cents amount.

    For computed categories (commute, home office) callers are expected to
    have already run the relevant deductions.* algorithm to turn structured
    inputs (distance_km, days_claimed, ...) into a cents amount before
    constructing this dataclass — core.py only aggregates, it does not know
    about category-specific business rules.
    """

    category: str
    amount_cents: int

    def __post_init__(self) -> None:
        if self.amount_cents < 0:
            raise InvalidIncomeError(
                f"Deduction amount for category={self.category!r} cannot be negative "
                f"(got {self.amount_cents} cents)."
            )


def calculate_werbungskosten(deductions: list[DeductionLine]) -> int:
    """Sum all real (documented) Werbungskosten line items.

    Args:
        deductions: resolved deduction line items for a single user/tax_year.

    Returns:
        Total real Werbungskosten in cents. Zero if the list is empty.
    """
    return sum(line.amount_cents for line in deductions)


def apply_pauschbetrag_or_actual(real_werbungskosten_cents: int, tax_year: int) -> int:
    """Apply the Arbeitnehmer-Pauschbetrag rule (§9a Satz 1 Nr. 1a EStG).

    The Finanzamt automatically grants a flat-rate deduction (the
    Pauschbetrag) regardless of whether the taxpayer documents any expenses.
    Documented (actual) Werbungskosten only matter once they *exceed* this
    flat rate — the taxpayer always receives the greater of the two ("Günstigerprüfung"
    is not needed here since the comparison is a simple maximum).

    Args:
        real_werbungskosten_cents: sum of documented, receipted deductions
            (typically the output of `calculate_werbungskosten`).
        tax_year: which year's Pauschbetrag to apply.

    Returns:
        The Werbungskosten amount to actually use in the tax calculation —
        either the real total or the statutory Pauschbetrag, whichever is
        larger.
    """
    if real_werbungskosten_cents < 0:
        raise InvalidIncomeError("real_werbungskosten_cents cannot be negative.")

    constants = get_constants_for_year(tax_year)
    return max(real_werbungskosten_cents, constants.arbeitnehmer_pauschbetrag_cents)


def apply_sonderausgaben_pauschbetrag(
    real_sonderausgaben_cents: int,
    is_joint_assessment: bool,
    tax_year: int,
) -> int:
    """Apply the Sonderausgaben-Pauschbetrag rule (§10c EStG).

    Mirrors `apply_pauschbetrag_or_actual` — the Finanzamt automatically
    grants a small flat-rate deduction for "special expenses" (Sonderausgaben:
    donations, church tax paid, certain insurance premiums not already
    counted elsewhere) regardless of documentation, and the taxpayer keeps
    the greater of that flat rate or their documented actual total. The
    flat amount doubles for jointly-assessed couples.

    Args:
        real_sonderausgaben_cents: sum of documented Sonderausgaben, e.g.
            the output of deductions.donations.calculate_spenden_deduction
            plus any other resolved Sonderausgaben line items.
        is_joint_assessment: mirrors `users.is_joint_assessment`.
        tax_year: which year's Pauschbetrag to apply.

    Returns:
        The Sonderausgaben amount to actually use — either the real total
        or the statutory flat rate, whichever is larger.
    """
    if real_sonderausgaben_cents < 0:
        raise InvalidIncomeError("real_sonderausgaben_cents cannot be negative.")

    constants = get_constants_for_year(tax_year)
    pauschbetrag_cents = (
        constants.sonderausgaben_pauschbetrag_joint_cents
        if is_joint_assessment
        else constants.sonderausgaben_pauschbetrag_single_cents
    )
    return max(real_sonderausgaben_cents, pauschbetrag_cents)


def calculate_taxable_income(
    gross_income_cents: int,
    werbungskosten_cents: int,
    other_deductions_cents: int = 0,
) -> int:
    """Derive zu versteuerndes Einkommen (zvE) — the taxable income base.

    This is a simplified MVP derivation covering the employee-income case
    (Einkünfte aus nichtselbständiger Arbeit) only: it does not yet account
    for Sonderausgaben-Pauschbetrag, Kinderfreibetrag, or other income
    categories (capital gains, rental, self-employment). Those are separate
    future modules that would compose with this function's output.

    Args:
        gross_income_cents: Brutto wage income (sum of
            wage_tax_certificates.gross_wage_cents for the year).
        werbungskosten_cents: output of `apply_pauschbetrag_or_actual` —
            the greater of actual or flat-rate work-related expense deduction.
        other_deductions_cents: additional Sonderausgaben/außergewöhnliche
            Belastungen already resolved to cents (default 0 for MVP scope).

    Returns:
        Taxable income in cents, floored at 0 (income tax law does not
        produce negative taxable income at this stage — losses carried
        forward are a distinct mechanism, out of scope for the MVP).
    """
    if gross_income_cents < 0:
        raise InvalidIncomeError("gross_income_cents cannot be negative.")
    if werbungskosten_cents < 0:
        raise InvalidIncomeError("werbungskosten_cents cannot be negative.")
    if other_deductions_cents < 0:
        raise InvalidIncomeError("other_deductions_cents cannot be negative.")

    taxable_income = gross_income_cents - werbungskosten_cents - other_deductions_cents
    return max(taxable_income, 0)
