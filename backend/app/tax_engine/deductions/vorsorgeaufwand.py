"""
Vorsorgeaufwendungen (retirement & other provision expenses) — §10 Abs. 1
Nr. 2, 3, 3a, Abs. 3, Abs. 4 EStG.

Two legally distinct sub-categories, each with its OWN cap mechanism --
NEITHER shares the small €36/€72 Sonderausgaben-Pauschbetrag (§10c EStG,
see core.apply_sonderausgaben_pauschbetrag) that donations/childcare/etc.
compare against, since real Vorsorgeaufwand for anyone with wage income
almost always dwarfs that flat rate:

1. Altersvorsorgeaufwendungen (§10 Abs. 1 Nr. 2, Abs. 3 EStG) — statutory
   pension insurance (gesetzliche Rentenversicherung) contributions,
   100% deductible since 2023 (the phase-in originally scheduled through
   2025 was accelerated by the 2022 Gesetz zur Vermeidung der
   Doppelbesteuerung von Alterseinkünften), capped at a Höchstbetrag that
   doubles for jointly-assessed couples.

2. Sonstige Vorsorgeaufwendungen (§10 Abs. 1 Nr. 3, 3a, Abs. 4 EStG) --
   health and long-term-care insurance contributions covering the
   statutory minimum benefit level (Basisabsicherung) are ALWAYS fully
   deductible with NO cap (Bürgerentlastungsgesetz Krankenversicherung
   2010); other sonstige Vorsorgeaufwendungen (unemployment insurance
   here) only count toward a separate Höchstbetrag that Basisabsicherung
   alone almost always already exceeds.

Scope simplifications (documented, not guessed at):
- Altersvorsorgeaufwendungen: this project only has each WageTaxCertificate's
  EMPLOYEE-side pension contribution (`pension_insurance_employee_cents`),
  not the employer's share. The full §10 Abs. 3 formula sums employee +
  employer contributions, multiplies by the year's percentage, then
  SUBTRACTS the tax-free employer share back out -- at 100% deductibility
  (2023+) those two steps cancel algebraically, leaving "employee
  contribution, capped at the Höchstbetrag" as the correct net result, so
  the employer's share was never actually needed here. This stops being
  exact only in a year where the percentage is below 100% (pre-2023) --
  not a concern for any tax_year this module currently supports.
- Rürup-Basisrente (private pension) contributions are NOT captured --
  no data model field collects them yet.
- Riester-Rente (AV) is a separate allowance (Zulage or Sonderausgabenabzug,
  whichever is more favorable) and is NOT modeled.
- The ~4% Krankengeld-Kürzung some statutorily-insured employees'
  contributions are technically subject to (the portion of gesetzliche KV
  funding sick pay, which isn't part of Basisabsicherung) is NOT applied --
  `health_insurance_employee_cents` is treated as fully Basisabsicherung.
- The €1,900/€2,800 sonstige-Vorsorgeaufwendungen Höchstbetrag distinguishes
  employees from the self-employed (who bear their own health insurance
  cost without an employer subsidy) -- this module always uses the
  employee rate. A self-employed user's true cap (€2,800) is understated,
  which almost never matters in practice since Basisabsicherung alone
  (uncapped) is what actually gets applied in the near-universal case
  where it already exceeds either cap.
"""

from __future__ import annotations

from app.tax_engine.constants import get_constants_for_year
from app.tax_engine.deductions.errors import DeductionValidationError


def calculate_altersvorsorge_deduction(
    pension_insurance_employee_cents: int,
    is_joint_assessment: bool,
    tax_year: int = 2024,
) -> int:
    """Deductible Altersvorsorgeaufwendungen for the year.

    Args:
        pension_insurance_employee_cents: sum of every
            WageTaxCertificate.pension_insurance_employee_cents for the
            user/tax_year (statutory pension insurance only -- see module
            docstring for why the employer share isn't a separate input).
        is_joint_assessment: mirrors users.is_joint_assessment -- doubles
            the Höchstbetrag (§10 Abs. 3 Satz 4 EStG).
        tax_year: which year's percentage/Höchstbetrag to apply.

    Returns:
        Deductible amount in cents: contributions capped at the
        Höchstbetrag, then reduced by the year's deductible fraction
        (100% for 2023 onward).
    """
    if pension_insurance_employee_cents < 0:
        raise DeductionValidationError("pension_insurance_employee_cents cannot be negative.")

    constants = get_constants_for_year(tax_year)
    hoechstbetrag_cents = (
        constants.altersvorsorge_hoechstbetrag_joint_cents
        if is_joint_assessment
        else constants.altersvorsorge_hoechstbetrag_single_cents
    )
    capped_cents = min(pension_insurance_employee_cents, hoechstbetrag_cents)
    return int(capped_cents * constants.altersvorsorge_deductible_fraction)


def calculate_sonstige_vorsorgeaufwendungen_deduction(
    health_insurance_employee_cents: int,
    long_term_care_insurance_employee_cents: int,
    unemployment_insurance_employee_cents: int,
    is_joint_assessment: bool,
    tax_year: int = 2024,
) -> int:
    """Deductible sonstige Vorsorgeaufwendungen for the year.

    Args:
        health_insurance_employee_cents, long_term_care_insurance_employee_cents:
            sums of the matching WageTaxCertificate fields -- treated as
            fully Basisabsicherung (see module docstring's simplification
            note), so always fully deductible with no cap.
        unemployment_insurance_employee_cents: sum of every
            WageTaxCertificate.unemployment_insurance_employee_cents --
            only counts toward the separate, capped bucket below.
        is_joint_assessment: mirrors users.is_joint_assessment -- doubles
            the Höchstbetrag.
        tax_year: which year's Höchstbetrag to apply.

    Returns:
        Deductible amount in cents: the greater of (a) uncapped
        Basisabsicherung alone, or (b) all sonstige Vorsorgeaufwendungen
        combined, capped at the Höchstbetrag -- per §10 Abs. 4 EStG, (a)
        can never be reduced by the cap even if (b) would land below it,
        which is exactly why this isn't a plain min().
    """
    for label, value in (
        ("health_insurance_employee_cents", health_insurance_employee_cents),
        ("long_term_care_insurance_employee_cents", long_term_care_insurance_employee_cents),
        ("unemployment_insurance_employee_cents", unemployment_insurance_employee_cents),
    ):
        if value < 0:
            raise DeductionValidationError(f"{label} cannot be negative.")

    constants = get_constants_for_year(tax_year)
    hoechstbetrag_cents = (
        constants.sonstige_vorsorgeaufwendungen_hoechstbetrag_joint_cents
        if is_joint_assessment
        else constants.sonstige_vorsorgeaufwendungen_hoechstbetrag_single_cents
    )

    basisabsicherung_cents = health_insurance_employee_cents + long_term_care_insurance_employee_cents
    all_sonstige_cents = basisabsicherung_cents + unemployment_insurance_employee_cents

    return max(basisabsicherung_cents, min(all_sonstige_cents, hoechstbetrag_cents))
