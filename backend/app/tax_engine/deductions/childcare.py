"""
Kinderbetreuungskosten (childcare costs) — §10 Abs. 1 Nr. 5 EStG.

Costs for third-party childcare (Kita, Tagesmutter, after-school care, ...)
for children under 14 are deductible as Sonderausgaben at 2/3 of the cost,
capped at €4,000 per child per year (2024 law — raised to 80% / €4,800 from
2025 onward; re-verify constants.py before reusing this module for a later
tax year). The German Federal Fiscal Court (BFH) requires payment by bank
transfer to the care provider's account — cash payments are not deductible,
which is a documentation/evidence requirement for the API layer to enforce
via required proof-of-payment upload, not something this pure calculation
function can validate.

Scope simplification: this MVP takes a single aggregate `total_costs_cents`
and a `number_of_children` count rather than a per-child cost breakdown.
The €4,000 cap is applied per child, so the aggregate cap here is
`number_of_children * per_child_cap`. This is exact when costs are
distributed evenly across children, and a reasonable (slightly generous)
approximation otherwise — a future per-child structured input would remove
this approximation entirely.
"""

from __future__ import annotations

from decimal import ROUND_DOWN, Decimal

from app.tax_engine.constants import get_constants_for_year
from app.tax_engine.deductions.errors import DeductionValidationError

_CENTS_PER_EURO = Decimal("100")


def calculate_childcare_deduction(
    total_costs_cents: int,
    number_of_children: int,
    tax_year: int = 2024,
) -> int:
    """Compute the deductible portion of childcare costs for the year.

    Args:
        total_costs_cents: documented, bank-transferred childcare costs
            across all qualifying children for the year.
        number_of_children: count of children (under 14) the costs relate
            to. Must be >= 1 if total_costs_cents > 0.
        tax_year: which year's fraction/cap to apply.

    Returns:
        The deductible amount, in cents.

    Raises:
        DeductionValidationError: on negative costs, a non-positive child
            count, or a positive cost with zero children (an inconsistent
            input the API layer should never produce).
    """
    if total_costs_cents < 0:
        raise DeductionValidationError("total_costs_cents cannot be negative.")
    if number_of_children < 0:
        raise DeductionValidationError("number_of_children cannot be negative.")
    if total_costs_cents > 0 and number_of_children == 0:
        raise DeductionValidationError(
            "total_costs_cents > 0 requires number_of_children >= 1."
        )

    if total_costs_cents == 0 or number_of_children == 0:
        return 0

    constants = get_constants_for_year(tax_year)

    deductible_fraction_euro = (
        Decimal(total_costs_cents) / _CENTS_PER_EURO
    ) * constants.childcare_deductible_fraction
    fraction_cents = int(deductible_fraction_euro.quantize(Decimal("1"), rounding=ROUND_DOWN)) * 100

    cap_cents = number_of_children * constants.childcare_max_deductible_cents_per_child

    return min(fraction_cents, cap_cents)
