"""
Entfernungspauschale — commute allowance (§9 Abs. 1 Satz 3 Nr. 4 EStG).

Algorithm workflow (see module docstring section 3 of the architecture spec):
    1. Validate inputs (non-negative, plausible bounds).
    2. Split the one-way commute distance into the two statutory tiers.
    3. Multiply each tier's km by its per-km rate to get a per-day allowance.
    4. Multiply the per-day allowance by the number of days actually worked
       on-site that year (Aggregate).
    5. Apply a plausibility sanity-cap on days_worked to catch data-entry
       errors before they become an inflated refund estimate.

Scope note (MVP): the statutory €4,500/year cap that applies specifically
when the taxpayer does NOT use their own vehicle (public transport, carpool
passenger, bike, on foot) is NOT yet implemented — that cap requires
knowing the mode of transport, which is a future input field. Vehicle-owner
commuters (the common case) have no such cap. This is flagged rather than
silently guessed at.
"""

from __future__ import annotations

from app.tax_engine.constants import get_constants_for_year
from app.tax_engine.deductions.errors import DeductionValidationError

# Plausibility ceiling: even with weekend/holiday work, no employee
# realistically commutes on-site more than this many days in a calendar
# year (365 days minus a token allowance for weekends/holidays). Values
# above this are rejected as a likely data-entry error rather than silently
# accepted and inflating the refund estimate.
_MAX_PLAUSIBLE_DAYS_WORKED = 280

# Plausibility ceiling on one-way distance — guards against a unit-entry
# error (e.g. meters instead of km).
_MAX_PLAUSIBLE_DISTANCE_KM = 300


def calculate_entfernungspauschale(distance_km: int, days_worked: int, tax_year: int = 2024) -> int:
    """Compute the Entfernungspauschale (commute allowance) in cents.

    Args:
        distance_km: one-way commute distance in full kilometers between
            home and first place of work ("erste Tätigkeitsstätte"). Partial
            kilometers are legally rounded down before this function is
            called (the API layer should floor() any fractional input).
        days_worked: number of days in the tax year the commute was
            actually made on-site.
        tax_year: which year's per-km rates to apply.

    Returns:
        Total commute allowance for the year, in cents.

    Raises:
        DeductionValidationError: on negative or implausible inputs.
    """
    if distance_km < 0:
        raise DeductionValidationError("distance_km cannot be negative.")
    if days_worked < 0:
        raise DeductionValidationError("days_worked cannot be negative.")
    if distance_km > _MAX_PLAUSIBLE_DISTANCE_KM:
        raise DeductionValidationError(
            f"distance_km={distance_km} exceeds the plausibility ceiling "
            f"({_MAX_PLAUSIBLE_DISTANCE_KM} km one-way). Check for a unit error."
        )
    if days_worked > _MAX_PLAUSIBLE_DAYS_WORKED:
        raise DeductionValidationError(
            f"days_worked={days_worked} exceeds the plausibility ceiling "
            f"({_MAX_PLAUSIBLE_DAYS_WORKED} days/year)."
        )

    if distance_km == 0 or days_worked == 0:
        return 0

    constants = get_constants_for_year(tax_year)
    first_tier_km = min(distance_km, constants.commute_rate_first_tier_km_threshold)
    remaining_km = max(distance_km - constants.commute_rate_first_tier_km_threshold, 0)

    per_day_allowance_cents = (
        first_tier_km * constants.commute_rate_cents_per_km_first_20
        + remaining_km * constants.commute_rate_cents_per_km_beyond_20
    )

    return per_day_allowance_cents * days_worked
