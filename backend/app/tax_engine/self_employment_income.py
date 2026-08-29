"""
Self-employment income (Einkünfte aus Gewerbebetrieb §15 EStG, or
selbständiger Arbeit §18 EStG for liberal professions) — computed via a
simplified Einnahmen-Überschuss-Rechnung (EÜR, §4 Abs. 3 EStG): revenue
minus operating expenses.

The arithmetic here is IDENTICAL to rental_income.calculate_rental_income
(revenue - expenses, signed result), but is deliberately a separate
function/module rather than a shared helper: §15/§18 income is a legally
distinct Einkunftsart from §21 rental income, with its own compliance
requirements (EÜR/Anlage S vs. Anlage V) and — most importantly — future
self-employment-specific rules (Kleinunternehmerregelung §19 UStG,
Gewerbesteuer, Freibetrag für Betriebsveräußerungsgewinne §16 Abs. 4 EStG)
that do NOT apply to rental income at all. Keeping them separate now avoids
an artificial shared abstraction that would need to be unpicked later.

*** SCOPE LIMITATION: Gewerbesteuer (trade tax) is NOT modeled. ***
Einkünfte aus Gewerbebetrieb (but not selbständiger Arbeit / liberal
professions) are additionally subject to Gewerbesteuer — a separate tax
with its own €24,500 allowance and a municipality-specific Hebesatz
multiplier, which then partially credits back against income tax via §35
EStG (Gewerbesteueranrechnung). That entire mechanism is unbuilt; this
module only feeds the EÜR profit/loss into the regular progressive income
tax base, which is correct for freelancers/liberal professions (the more
common case for this product's target user base) but understates the true
liability for a Gewerbebetrieb.

Like rental income, the result MAY BE NEGATIVE (a business loss), and
feeds into `core.calculate_taxable_income`'s `other_income_categories_cents`
parameter alongside net rental income — NOT floored at zero first.
"""

from __future__ import annotations

from app.tax_engine.core import InvalidIncomeError


def calculate_self_employment_income(gross_revenue_cents: int, deductible_expenses_cents: int) -> int:
    """Compute self-employment profit/loss for one business/year via a
    simplified EÜR (revenue minus operating expenses).

    Args:
        gross_revenue_cents: Betriebseinnahmen (business revenue received)
            for the year.
        deductible_expenses_cents: documented Betriebsausgaben (operating
            expenses) for the year.

    Returns:
        Net self-employment income for the year, in cents. MAY BE
        NEGATIVE — a documented business loss is a legitimate result.

    Raises:
        InvalidIncomeError: if either individual input is negative (only
            their DIFFERENCE may be negative, not the inputs themselves).
    """
    if gross_revenue_cents < 0:
        raise InvalidIncomeError("gross_revenue_cents cannot be negative.")
    if deductible_expenses_cents < 0:
        raise InvalidIncomeError("deductible_expenses_cents cannot be negative.")

    return gross_revenue_cents - deductible_expenses_cents
