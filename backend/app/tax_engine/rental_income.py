"""
Rental income (Einkünfte aus Vermietung und Verpachtung) — §21 EStG.

Unlike employment income, there is NO flat-rate Pauschbetrag fallback for
rental Werbungskosten — every deductible expense must be documented
(AfA/depreciation, mortgage interest, repairs, management costs, etc.).
The result MAY BE NEGATIVE (a rental loss), and unlike employment
Werbungskosten (which only floor taxable employment income at zero), a
negative rental result legally offsets OTHER positive income at the
Gesamtbetrag der Einkünfte level (§2 Abs. 3 EStG horizontal loss
offsetting). This function's signed output feeds directly into
`core.calculate_taxable_income`'s `other_income_categories_cents`
parameter — callers must NOT floor it at zero first.

Scope limitation: this MVP does not compute an AfA depreciation schedule
(§7 Abs. 4/5 EStG — requires tracking acquisition cost, the building-vs-
land split, and construction year to pick the correct 2%/2.5%/declining
rate) or Verlustvortrag (carrying a loss forward when it exceeds all other
income in a single year). Depreciation is expected to be pre-computed and
submitted as one of the deductible expense line items for now.
"""

from __future__ import annotations

from app.tax_engine.core import InvalidIncomeError


def calculate_rental_income(gross_rental_income_cents: int, deductible_expenses_cents: int) -> int:
    """Compute Einkünfte aus Vermietung und Verpachtung for one property/
    year.

    Args:
        gross_rental_income_cents: Mieteinnahmen (rent received, including
            passed-through ancillary cost payments) for the year.
        deductible_expenses_cents: documented Werbungskosten bei V+V — AfA,
            mortgage interest, repairs, management fees, etc. No flat-rate
            fallback exists for this category, unlike employment income.

    Returns:
        Net rental income for the property/year, in cents. MAY BE
        NEGATIVE — a documented loss is a legitimate, legally meaningful
        result, not an error condition.

    Raises:
        InvalidIncomeError: if either individual input is negative (only
            their DIFFERENCE may be negative, not the inputs themselves).
    """
    if gross_rental_income_cents < 0:
        raise InvalidIncomeError("gross_rental_income_cents cannot be negative.")
    if deductible_expenses_cents < 0:
        raise InvalidIncomeError("deductible_expenses_cents cannot be negative.")

    return gross_rental_income_cents - deductible_expenses_cents
