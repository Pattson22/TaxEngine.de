"""
AfA (Absetzung für Abnutzung) — linear building depreciation for rental
property, §7 Abs. 4 EStG.

Only the BUILDING portion of a property depreciates -- land never does,
which is exactly why this needs the building's own acquisition cost as a
separate input from any land value, rather than the property's total
purchase price. The applicable linear rate depends on when the building
was completed (Fertigstellung), not when it was purchased:

- Completed 2023 or later: 3% per year (raised from 2% by the
  Wachstumschancengesetz, effective for buildings completed after
  2022-12-31).
- Completed 1925 through 2022: 2% per year (the long-standing standard
  rate for residential buildings).
- Completed before 1925: 2.5% per year.

Scope simplifications (documented, not guessed at):
- No monthly pro-ration for a property acquired partway through the tax
  year -- this computes a full year of AfA regardless of when in the year
  the property was acquired. §7 Abs. 1 Satz 4 EStG actually pro-rates the
  FIRST year by month of acquisition; this MVP always returns the full
  annual amount, which overstates year-one depreciation for a mid-year
  purchase. A future per-month acquisition-date input would remove this.
- No declining-balance (degressive) AfA, Sonderabschreibung (§7b EStG),
  or denkmalgeschützte-Gebäude enhanced depreciation (§7i/7h EStG) --
  only the standard linear rate table above.
- This computes ONE YEAR's depreciation from the building's original
  acquisition cost; it does not track cumulative depreciation already
  claimed in prior years or cap the total at the building's value once
  fully depreciated (irrelevant within any single supported tax_year's
  standard 2-3% rate, since full depreciation takes 33-50 years).
"""

from __future__ import annotations

from decimal import Decimal

from app.tax_engine.core import InvalidIncomeError

_RATE_COMPLETED_2023_OR_LATER = Decimal("0.03")
_RATE_COMPLETED_1925_TO_2022 = Decimal("0.02")
_RATE_COMPLETED_BEFORE_1925 = Decimal("0.025")


def calculate_afa_deduction(building_acquisition_cost_cents: int, building_completion_year: int) -> int:
    """One year's linear AfA on a rental building.

    Args:
        building_acquisition_cost_cents: the BUILDING's own acquisition
            cost, excluding land value -- see module docstring for why
            this must already exclude land (which never depreciates).
        building_completion_year: the year the building was completed
            (Baujahr/Fertigstellungsjahr), which selects the rate --
            NOT the year it was acquired by the current owner.

    Returns:
        One year's deductible AfA amount, in cents.

    Raises:
        InvalidIncomeError: on a negative acquisition cost or an
            implausible completion year (before 1800, or after the
            current architectural reality of "not yet built").
    """
    if building_acquisition_cost_cents < 0:
        raise InvalidIncomeError("building_acquisition_cost_cents cannot be negative.")
    if building_completion_year < 1800 or building_completion_year > 2100:
        raise InvalidIncomeError(
            f"building_completion_year={building_completion_year} is not plausible."
        )

    if building_completion_year >= 2023:
        rate = _RATE_COMPLETED_2023_OR_LATER
    elif building_completion_year >= 1925:
        rate = _RATE_COMPLETED_1925_TO_2022
    else:
        rate = _RATE_COMPLETED_BEFORE_1925

    return int(Decimal(building_acquisition_cost_cents) * rate)
