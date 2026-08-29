"""
Kinderfreibetrag vs. Kindergeld — the Günstigerprüfung (§31, §32 Abs. 6 EStG).

Parents receive Kindergeld (child benefit) monthly throughout the year,
paid by the Familienkasse independently of the tax return. At assessment
time, the Finanzamt automatically checks whether the family would be
BETTER OFF claiming the Kinderfreibetrag + BEA-Freibetrag instead — a
combined allowance that reduces taxable income — but if that path is
taken, the Kindergeld already received during the year must be added back
to the resulting tax bill (it was effectively an advance against the
allowance, not a separate benefit stacked on top of it). The Finanzamt
keeps whichever of the two produces the LOWER final tax bill; the taxpayer
never has to choose or apply for this — it is automatic (§31 Satz 4 EStG).

Simplification (documented, not silently assumed): this module treats
"children" as a plain count rather than first-class entities with
birthdates/custody splits — matching the same simplification already used
in deductions/childcare.py. NOT modeled: partial-year eligibility (a child
born or turning 18 mid-year), the disabled-child Freibetrag extension, and
transferring a non-custodial parent's unused half of the allowance
(§32 Abs. 6 Satz 6 EStG) — which matters a lot in practice, since a
separately-assessed single parent with only their OWN half of the
Kinderfreibetrag will almost always be better off keeping Kindergeld (half
the allowance's tax saving rarely exceeds the full Kindergeld received),
even at the top marginal rate.

Scope note on Soli/Kirchensteuer: by law, the Bemessungsgrundlage for
Solidaritätszuschlag and Kirchensteuer always uses the income tax figure
AS IF the Kinderfreibetrag had been applied, even for families who come
out ahead keeping Kindergeld for income tax purposes (a genuine quirk of
§51a EStG / §3 SolZG). This module does NOT implement that — soli.py and
church_tax.py continue to compute their surcharges on the actually-assessed
(post-Günstigerprüfung) income tax, which can slightly understate Soli/KiSt
for the (uncommon) case of a family that is Kindergeld-better-off despite
owing Soli/KiSt in the first place.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.tax_engine.constants import get_constants_for_year
from app.tax_engine.core import InvalidIncomeError
from app.tax_engine.tax_brackets import calculate_income_tax_for_assessment


@dataclass(frozen=True)
class GuenstigerpruefungResult:
    """The outcome of comparing Kindergeld-kept vs. Kinderfreibetrag-applied."""

    final_income_tax_cents: int
    kinderfreibetrag_applied: bool
    kinderfreibetrag_total_cents: int
    income_tax_without_kinderfreibetrag_cents: int
    income_tax_with_kinderfreibetrag_cents: int


def calculate_kinderfreibetrag_total(
    number_of_children: int,
    is_joint_assessment: bool,
    tax_year: int = 2024,
) -> int:
    """Total Kinderfreibetrag + BEA-Freibetrag for the household.

    Raises:
        InvalidIncomeError: if number_of_children is negative.
    """
    if number_of_children < 0:
        raise InvalidIncomeError("number_of_children cannot be negative.")

    constants = get_constants_for_year(tax_year)
    per_child_cents = (
        constants.kinderfreibetrag_total_per_child_joint_cents
        if is_joint_assessment
        else constants.kinderfreibetrag_total_per_child_single_cents
    )
    return per_child_cents * number_of_children


def apply_kinderfreibetrag_guenstigerpruefung(
    zve_before_kinderfreibetrag_cents: int,
    number_of_children: int,
    is_joint_assessment: bool,
    kindergeld_received_cents: int,
    tax_year: int = 2024,
) -> GuenstigerpruefungResult:
    """Run the automatic Günstigerprüfung and return the more favorable
    final income tax figure.

    Args:
        zve_before_kinderfreibetrag_cents: zu versteuerndes Einkommen
            computed WITHOUT any Kinderfreibetrag applied — the normal
            output of core.calculate_taxable_income.
        number_of_children: count of children the household is entitled
            to claim (see module docstring for the "plain count" scope
            simplification).
        is_joint_assessment: mirrors `users.is_joint_assessment`.
        kindergeld_received_cents: total Kindergeld ACTUALLY paid out by
            the Familienkasse for the year (not a theoretical full-year
            figure) — this is what gets added back if the Kinderfreibetrag
            path wins.
        tax_year: which year's Freibetrag/tariff to apply.

    Returns:
        A GuenstigerpruefungResult carrying the winning final income tax
        figure plus enough detail (both computed amounts, which path won)
        for the API layer to show the user why.

    Raises:
        InvalidIncomeError: on negative zvE, children count, or Kindergeld.
    """
    if zve_before_kinderfreibetrag_cents < 0:
        raise InvalidIncomeError("zve_before_kinderfreibetrag_cents cannot be negative.")
    if kindergeld_received_cents < 0:
        raise InvalidIncomeError("kindergeld_received_cents cannot be negative.")

    tax_without = calculate_income_tax_for_assessment(
        zve_before_kinderfreibetrag_cents, tax_year, is_joint_assessment
    )

    if number_of_children == 0:
        # No children -> nothing to compare against; the Kindergeld path
        # trivially "wins" since there is no Kinderfreibetrag to apply.
        return GuenstigerpruefungResult(
            final_income_tax_cents=tax_without,
            kinderfreibetrag_applied=False,
            kinderfreibetrag_total_cents=0,
            income_tax_without_kinderfreibetrag_cents=tax_without,
            income_tax_with_kinderfreibetrag_cents=tax_without,
        )

    kinderfreibetrag_total_cents = calculate_kinderfreibetrag_total(
        number_of_children, is_joint_assessment, tax_year
    )
    zve_with_kinderfreibetrag_cents = max(
        zve_before_kinderfreibetrag_cents - kinderfreibetrag_total_cents, 0
    )
    tax_with_before_addback = calculate_income_tax_for_assessment(
        zve_with_kinderfreibetrag_cents, tax_year, is_joint_assessment
    )
    tax_with = tax_with_before_addback + kindergeld_received_cents

    if tax_with < tax_without:
        return GuenstigerpruefungResult(
            final_income_tax_cents=tax_with,
            kinderfreibetrag_applied=True,
            kinderfreibetrag_total_cents=kinderfreibetrag_total_cents,
            income_tax_without_kinderfreibetrag_cents=tax_without,
            income_tax_with_kinderfreibetrag_cents=tax_with,
        )

    return GuenstigerpruefungResult(
        final_income_tax_cents=tax_without,
        kinderfreibetrag_applied=False,
        kinderfreibetrag_total_cents=kinderfreibetrag_total_cents,
        income_tax_without_kinderfreibetrag_cents=tax_without,
        income_tax_with_kinderfreibetrag_cents=tax_with,
    )
