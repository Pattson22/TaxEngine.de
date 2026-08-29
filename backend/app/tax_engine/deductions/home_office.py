"""
Homeoffice-Pauschale — home office allowance (§4 Abs. 5 Satz 1 Nr. 6c EStG,
applied to employees via §9 Abs. 5 Satz 1 EStG).

Capping logic:
    - A flat rate is granted per calendar day the taxpayer worked
      predominantly from home.
    - The number of eligible days is capped annually at a statutory maximum
      (210 days for 2024, corresponding to a €1,260 annual ceiling at the
      current €6/day rate).
    - Inputs above the cap are NOT rejected as an error (unlike commute's
      plausibility ceiling) — claiming e.g. 230 home office days is legally
      normal (more working days than the cap exist in a year), so the
      correct behavior is to silently clamp to the statutory maximum, not
      to error out.

Business-rule note (documented, not yet enforced here): a given calendar
day cannot simultaneously earn both the Homeoffice-Pauschale AND the
Entfernungspauschale for a commute that didn't happen. Cross-deduction
mutual-exclusivity validation (comparing days_worked in commute.py against
days_claimed here for overlap) is intentionally out of scope for this
module — it belongs in a higher-level filing-validation pass that has
visibility into both deduction rows for the same user/tax_year.
"""

from __future__ import annotations

from app.tax_engine.constants import get_constants_for_year
from app.tax_engine.deductions.errors import DeductionValidationError


def calculate_homeoffice_pauschale(days_claimed: int, tax_year: int = 2024) -> int:
    """Compute the Homeoffice-Pauschale (home office allowance) in cents.

    Args:
        days_claimed: number of days in the tax year worked predominantly
            from home. May exceed the statutory cap (see module docstring)
            — this function clamps rather than rejects.
        tax_year: which year's rate/cap to apply.

    Returns:
        Total home office allowance for the year, in cents. Always
        `<= max_days * rate_per_day`.

    Raises:
        DeductionValidationError: if days_claimed is negative.
    """
    if days_claimed < 0:
        raise DeductionValidationError("days_claimed cannot be negative.")

    constants = get_constants_for_year(tax_year)
    eligible_days = min(days_claimed, constants.home_office_max_days_per_year)

    return eligible_days * constants.home_office_rate_cents_per_day
