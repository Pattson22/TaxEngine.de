"""
Außergewöhnliche Belastungen (extraordinary burdens) — §33 EStG.

Documented extraordinary, necessary, and appropriate expenses (medical
costs not covered by insurance, disability-related costs, funeral costs
exceeding the estate, etc.) are deductible, but only the portion
EXCEEDING the taxpayer's "zumutbare Belastung" (reasonable/expected own
contribution, §33 Abs. 3 EStG) -- a percentage of Gesamtbetrag der
Einkünfte that depends on income bracket, marital status, and number of
children. This is architecturally separate from Vorsorgeaufwendungen
(vorsorgeaufwand.py) and from the small §10c Sonderausgaben-Pauschbetrag:
its own dedicated threshold mechanism, never compared against either.

The zumutbare Belastung is computed in a STAGED/tiered manner across the
three income brackets -- each bracket's rate applies only to the slice of
Gesamtbetrag der Einkünfte that falls within it, exactly like the
progressive income tax brackets themselves, then the three slices are
summed. This follows the BFH's 2017 ruling (VI R 75/14), which overturned
the Finanzverwaltung's older practice of picking a single bracket by the
TOTAL amount and applying that one rate to the whole thing -- the older
method systematically understated the deduction (overstated the
taxpayer's zumutbare Belastung) for anyone whose income crossed a
bracket boundary.

Scope simplification: this module implements the general §33 Abs. 1-3
mechanism only. The Behinderten-Pauschbetrag (§33b EStG, a flat allowance
based on Grad der Behinderung that REPLACES rather than supplements this
calculation for disability-related costs) is NOT modeled -- it needs a
structured "degree of disability" input this project's data model doesn't
collect, and choosing between it and documented actual costs is itself a
separate Günstigerprüfung this module does not perform.
"""

from __future__ import annotations

from decimal import Decimal

from app.tax_engine.constants import get_constants_for_year
from app.tax_engine.deductions.errors import DeductionValidationError


def calculate_aussergewoehnliche_belastungen_deduction(
    total_costs_cents: int,
    gesamtbetrag_der_einkuenfte_cents: int,
    is_joint_assessment: bool,
    number_of_children: int,
    tax_year: int = 2024,
) -> int:
    """Deductible außergewöhnliche Belastungen for the year.

    Args:
        total_costs_cents: documented, extraordinary/necessary/appropriate
            costs for the year (e.g. unreimbursed medical expenses).
        gesamtbetrag_der_einkuenfte_cents: total income across every
            progressive-tariff category (the same figure the donation cap
            uses -- see tax_calculation_service.py) -- the base the
            zumutbare Belastung percentages apply to.
        is_joint_assessment: mirrors users.is_joint_assessment -- only
            relevant when number_of_children == 0 (§33 Abs. 3 EStG's table
            gives childless couples a lower rate than childless singles;
            the child-count columns apply regardless of marital status).
        number_of_children: mirrors tax_filings.number_of_children --
            selects the 1-2-Kinder or 3-plus-Kinder column when > 0.
        tax_year: which year's bracket thresholds/rates to apply.

    Returns:
        Deductible amount in cents: total_costs_cents minus the (staged)
        zumutbare Belastung, floored at 0 -- a shortfall isn't itself
        deductible elsewhere.
    """
    if total_costs_cents < 0:
        raise DeductionValidationError("total_costs_cents cannot be negative.")
    if gesamtbetrag_der_einkuenfte_cents < 0:
        raise DeductionValidationError("gesamtbetrag_der_einkuenfte_cents cannot be negative.")
    if number_of_children < 0:
        raise DeductionValidationError("number_of_children cannot be negative.")

    constants = get_constants_for_year(tax_year)

    if number_of_children >= 3:
        rates = constants.zumutbare_belastung_rates_three_plus_children
    elif number_of_children >= 1:
        rates = constants.zumutbare_belastung_rates_one_or_two_children
    elif is_joint_assessment:
        rates = constants.zumutbare_belastung_rates_joint_no_children
    else:
        rates = constants.zumutbare_belastung_rates_single_no_children

    bracket_1_threshold = constants.zumutbare_belastung_bracket_1_threshold_cents
    bracket_2_threshold = constants.zumutbare_belastung_bracket_2_threshold_cents

    slice_1_cents = min(gesamtbetrag_der_einkuenfte_cents, bracket_1_threshold)
    slice_2_cents = max(0, min(gesamtbetrag_der_einkuenfte_cents, bracket_2_threshold) - bracket_1_threshold)
    slice_3_cents = max(0, gesamtbetrag_der_einkuenfte_cents - bracket_2_threshold)

    zumutbare_belastung_cents = int(
        Decimal(slice_1_cents) * rates[0]
        + Decimal(slice_2_cents) * rates[1]
        + Decimal(slice_3_cents) * rates[2]
    )

    return max(total_costs_cents - zumutbare_belastung_cents, 0)
