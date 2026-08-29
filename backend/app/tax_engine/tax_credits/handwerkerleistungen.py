"""
Handwerkerleistungen (craftsperson services) — §35a Abs. 3 EStG.

A direct credit of 20% of LABOR cost (Arbeitskosten — materials, parts, and
travel surcharges are explicitly excluded by law and must be itemized
separately on the invoice) against the taxpayer's final tax liability,
capped at €1,200/year. This is the same statutory mechanism that also
covers haushaltsnahe Dienstleistungen (household services, 20%/€4,000 cap)
and haushaltsnahe Beschäftigungsverhältnisse (household employment,
20%/€510-€4,000 depending on employment type) — those two are NOT yet
implemented here; this module covers only the Handwerkerleistungen case
named in the current scope.

Documentation requirement (§35a Abs. 5 Satz 3 EStG): the credit is only
available if payment was made by bank transfer against an itemized
invoice — cash payments are categorically excluded, same evidence
requirement as childcare.py. Enforcing that is an API-layer/upload concern,
not something this pure function can validate.
"""

from __future__ import annotations

from app.tax_engine.constants import get_constants_for_year
from app.tax_engine.deductions.errors import DeductionValidationError


def calculate_handwerkerleistungen_credit(labor_cost_cents: int, tax_year: int = 2024) -> int:
    """Compute the §35a tax credit for craftsperson labor costs.

    Args:
        labor_cost_cents: the LABOR-only portion of invoiced craftsperson
            costs for the year (materials/parts excluded per statute).
        tax_year: which year's rate/cap to apply.

    Returns:
        The credit amount, in cents, to subtract from the final assessed
        tax liability via tax_credits.apply_tax_credit. Always
        `<= handwerkerleistungen_max_credit_cents`.

    Raises:
        DeductionValidationError: if labor_cost_cents is negative.
    """
    if labor_cost_cents < 0:
        raise DeductionValidationError("labor_cost_cents cannot be negative.")

    if labor_cost_cents == 0:
        return 0

    constants = get_constants_for_year(tax_year)
    uncapped_credit_cents = int(labor_cost_cents * constants.handwerkerleistungen_credit_fraction)

    return min(uncapped_credit_cents, constants.handwerkerleistungen_max_credit_cents)
