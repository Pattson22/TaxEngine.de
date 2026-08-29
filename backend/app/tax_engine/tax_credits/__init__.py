"""
Tax CREDITS (Steuerermäßigungen) — amounts subtracted directly from the
FINAL ASSESSED TAX LIABILITY, as distinct from deductions (Werbungskosten,
Sonderausgaben), which reduce TAXABLE INCOME before the progressive tariff
is even applied. Mixing the two up produces a materially wrong refund
estimate, so they deliberately live in a separate package from
`deductions/` with a different application point in the calculation
pipeline: credits are applied AFTER `tax_brackets.calculate_income_tax*`,
not before.
"""

from __future__ import annotations


def apply_tax_credit(assessed_tax_cents: int, credit_cents: int) -> int:
    """Subtract a Steuerermäßigung credit from an assessed tax amount.

    Shared by every credit module (currently just Handwerkerleistungen) so
    the "never go below zero" floor logic — a taxpayer's credits can reduce
    their tax to zero but never turn income tax into a negative
    number/payment from the state via this mechanism — lives in one place.

    Args:
        assessed_tax_cents: income tax (or income tax + Soli + church tax,
            depending on what the caller wants credited against) before
            this credit is applied.
        credit_cents: the credit amount, e.g. from
            handwerkerleistungen.calculate_handwerkerleistungen_credit.

    Returns:
        The tax amount after applying the credit, floored at 0.
    """
    if assessed_tax_cents < 0:
        raise ValueError("assessed_tax_cents cannot be negative.")
    if credit_cents < 0:
        raise ValueError("credit_cents cannot be negative.")

    return max(assessed_tax_cents - credit_cents, 0)
