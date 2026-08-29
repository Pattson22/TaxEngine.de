"""
Centralized, year-versioned tax constants.

Every legally-defined amount used by the calculation engine lives here and
ONLY here. No module under `tax_engine` should hard-code a Euro figure or a
bracket threshold — this keeps the annual "new tax year" update to a single
file review instead of a codebase-wide audit.

All monetary constants are expressed in integer CENTS.

Sources: Bundesministerium der Finanzen (BMF) annual tax tables, §32a EStG,
§9a EStG, §9 Abs. 1 Nr. 4 EStG, §4 Abs. 5 Satz 1 Nr. 6c EStG.

IMPORTANT: These values must be re-verified against the official BMF
publication at the start of every new tax year before this module is used
for a filing in that year. Treat this file as a compliance artifact, not
just code — changes should be reviewed like a legal document, not a
routine PR.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TaxYearConstants:
    """Immutable snapshot of the constants that apply to a single tax year."""

    tax_year: int

    # §9a Satz 1 Nr. 1a EStG — Arbeitnehmer-Pauschbetrag (flat deduction
    # applied automatically unless documented Werbungskosten exceed it).
    arbeitnehmer_pauschbetrag_cents: int

    # §32a Abs. 1 EStG — Grundfreibetrag, the tax-free minimum subsistence
    # threshold below which no income tax is owed.
    grundfreibetrag_cents: int

    # §9 Abs. 1 Satz 3 Nr. 4 EStG — Entfernungspauschale rates (per km, per
    # working day, one-way commute distance).
    commute_rate_cents_per_km_first_20: int
    commute_rate_cents_per_km_beyond_20: int
    commute_rate_first_tier_km_threshold: int

    # §4 Abs. 5 Satz 1 Nr. 6c EStG — Homeoffice-Pauschale.
    home_office_rate_cents_per_day: int
    home_office_max_days_per_year: int

    # §32a Abs. 1 EStG bracket thresholds (zu versteuerndes Einkommen, cents)
    # used by tax_brackets.calculate_income_tax. See that module for the
    # full piecewise formula these thresholds feed into.
    bracket_2_threshold_cents: int   # end of Grundfreibetrag zone
    bracket_3_threshold_cents: int   # end of first progression zone
    bracket_4_threshold_cents: int   # end of second progression zone (start of 42% zone)
    bracket_5_threshold_cents: int   # start of the 45% "Reichensteuer" zone

    # §4 SolZG 1995 — Solidaritätszuschlag Freigrenze (exemption threshold,
    # applied to the ASSESSED INCOME TAX, not to income) and the
    # Milderungszone (tapering) rate that applies just above it.
    soli_freigrenze_single_cents: int
    soli_freigrenze_joint_cents: int
    soli_rate: Decimal                 # flat 5.5% once fully phased in
    soli_milderungszone_rate: Decimal  # 11.9% tapering rate near the Freigrenze

    # §51a EStG / Landeskirchensteuergesetze — Kirchensteuer rate as a
    # percentage of assessed income tax. Bayern and Baden-Württemberg are
    # the two states with the lower 8% rate; all other Bundesländer levy 9%.
    church_tax_rate_bavaria_bw: Decimal
    church_tax_rate_other_states: Decimal

    # §10c EStG — Sonderausgaben-Pauschbetrag, granted automatically unless
    # documented Sonderausgaben (donations, church tax paid, etc.) exceed it.
    sonderausgaben_pauschbetrag_single_cents: int
    sonderausgaben_pauschbetrag_joint_cents: int

    # §10b Abs. 1 EStG — Spenden (donations) are deductible as Sonderausgaben
    # up to this percentage of the Gesamtbetrag der Einkünfte (total income).
    spenden_deduction_cap_percentage: Decimal

    # §10 Abs. 1 Nr. 5 EStG — Kinderbetreuungskosten (childcare costs) are
    # deductible at this fraction, capped per child per year.
    childcare_deductible_fraction: Decimal
    childcare_max_deductible_cents_per_child: int

    # §35a Abs. 3 EStG — Handwerkerleistungen (craftsperson services): a
    # direct credit against the FINAL TAX LIABILITY (not a deduction from
    # taxable income) equal to this fraction of labor costs, capped annually.
    handwerkerleistungen_credit_fraction: Decimal
    handwerkerleistungen_max_credit_cents: int


# -----------------------------------------------------------------------------
# 2024 tax year (also used as the 2025 placeholder pending official BMF
# publication of final 2025 bracket coefficients — verify before production use).
# -----------------------------------------------------------------------------
TAX_YEAR_2024 = TaxYearConstants(
    tax_year=2024,
    arbeitnehmer_pauschbetrag_cents=123_000,       # €1,230
    grundfreibetrag_cents=11_604_00,               # €11,604
    commute_rate_cents_per_km_first_20=30,          # €0.30/km
    commute_rate_cents_per_km_beyond_20=38,         # €0.38/km (extended through 2026)
    commute_rate_first_tier_km_threshold=20,
    home_office_rate_cents_per_day=600,             # €6.00/day
    home_office_max_days_per_year=210,
    bracket_2_threshold_cents=17_005_00,            # €17,005
    bracket_3_threshold_cents=66_760_00,            # €66,760
    bracket_4_threshold_cents=277_825_00,           # €277,825
    bracket_5_threshold_cents=277_825_00,           # 45% zone starts where 42% zone ends
    soli_freigrenze_single_cents=18_130_00,         # €18,130 of assessed income tax
    soli_freigrenze_joint_cents=36_260_00,          # €36,260 of assessed income tax
    soli_rate=Decimal("0.055"),
    soli_milderungszone_rate=Decimal("0.119"),
    church_tax_rate_bavaria_bw=Decimal("0.08"),
    church_tax_rate_other_states=Decimal("0.09"),
    sonderausgaben_pauschbetrag_single_cents=3_600,  # €36
    sonderausgaben_pauschbetrag_joint_cents=7_200,   # €72
    spenden_deduction_cap_percentage=Decimal("0.20"),
    childcare_deductible_fraction=Decimal("0.6667"),  # 2/3, per 2024 law (raised to 80% from 2025)
    childcare_max_deductible_cents_per_child=400_000,  # €4,000/child (2024)
    handwerkerleistungen_credit_fraction=Decimal("0.20"),
    handwerkerleistungen_max_credit_cents=120_000,   # €1,200/year cap on the credit itself
)

SUPPORTED_TAX_YEARS: dict[int, TaxYearConstants] = {
    2024: TAX_YEAR_2024,
}


def get_constants_for_year(tax_year: int) -> TaxYearConstants:
    """Look up the immutable constant set for a given tax year.

    Raises ValueError for any year we have not explicitly reviewed and
    published constants for — silently falling back to a neighboring year's
    values would risk an incorrect tax calculation, which is unacceptable in
    a financial system.
    """
    try:
        return SUPPORTED_TAX_YEARS[tax_year]
    except KeyError as exc:
        raise ValueError(
            f"No verified tax constants available for tax_year={tax_year}. "
            f"Supported years: {sorted(SUPPORTED_TAX_YEARS)}. "
            "Add a reviewed TaxYearConstants entry before filing this year."
        ) from exc
