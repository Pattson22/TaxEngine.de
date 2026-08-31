"""
Capital gains (Kapitalerträge) — §20 EStG income (interest, dividends,
realized gains on securities), taxed under the flat Abgeltungsteuer regime
(§32d EStG) rather than the progressive §32a tariff used for employment
income.

Pipeline:
    gross capital income (sum of capital_income_statements.gross_income_cents)
      -> apply_sparer_pauschbetrag()      §20 Abs. 9 EStG allowance
      -> calculate_kapitalertragsteuer()  25%, or a reduced rate if church-tax-liable
      -> soli.calculate_solidaritaetszuschlag_on_capital_gains_tax()   flat 5.5%, no Freigrenze
      -> church_tax.calculate_kirchensteuer()   same function used for regular income tax

§32d Abs. 6 EStG Günstigerprüfung: a taxpayer whose personal marginal
income tax rate is below 25% can elect to have capital gains taxed under
the regular progressive tariff instead of the flat Abgeltungsteuer, the
same "run both, keep whichever is cheaper, automatically" pattern as
tax_engine/kinderfreibetrag.py's Kindergeld/Kinderfreibetrag comparison
(see apply_capital_gains_guenstigerpruefung below). It is also NOT the
"greater of" comparison pattern from Werbungskosten — since 2009,
individual investment-related costs are not separately deductible at all,
so the subtraction in apply_sparer_pauschbetrag is a hard subtraction,
not a max().

Scope simplification: apply_capital_gains_guenstigerpruefung folds capital
income into the taxable income figure BEFORE any Kinderfreibetrag
adjustment (tax_calculation_service.py's taxable_income_cents), not the
Kinderfreibetrag-adjusted figure its own Günstigerprüfung separately
settles on -- the two elections' interaction (whether folding capital
gains in changes which Kinderfreibetrag path is more favorable, or vice
versa) is not modeled. Each election is correct in isolation; a
theoretical taxpayer exactly at the boundary of both could see a
marginally suboptimal combined outcome.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal

from app.tax_engine.constants import get_constants_for_year
from app.tax_engine.core import InvalidIncomeError
from app.tax_engine.enums import LOW_CHURCH_TAX_RATE_STATES, ChurchTaxType, FederalState
from app.tax_engine.tax_brackets import calculate_income_tax_for_assessment

_CENTS_PER_EURO = Decimal("100")


def apply_sparer_pauschbetrag(
    gross_capital_income_cents: int,
    is_joint_assessment: bool,
    tax_year: int = 2024,
) -> int:
    """Apply the Sparer-Pauschbetrag (§20 Abs. 9 EStG).

    Returns the TAXABLE portion of capital income after the allowance,
    floored at 0 — an allowance can shield income but never manufacture a
    negative taxable amount.

    Raises:
        InvalidIncomeError: if gross_capital_income_cents is negative.
    """
    if gross_capital_income_cents < 0:
        raise InvalidIncomeError("gross_capital_income_cents cannot be negative.")

    constants = get_constants_for_year(tax_year)
    pauschbetrag_cents = (
        constants.sparer_pauschbetrag_joint_cents
        if is_joint_assessment
        else constants.sparer_pauschbetrag_single_cents
    )
    return max(gross_capital_income_cents - pauschbetrag_cents, 0)


def calculate_kapitalertragsteuer(
    taxable_capital_income_cents: int,
    church_tax_type: ChurchTaxType,
    residence_state: FederalState,
    tax_year: int = 2024,
) -> int:
    """Compute Kapitalertragsteuer (KapESt) under the flat Abgeltungsteuer.

    The standard rate is 25%. For church-tax-liable taxpayers, banks
    withhold KapESt at a REDUCED rate, because church tax on capital
    income is itself deductible against that income before the 25% rate
    applies. The net effect collapses to a closed-form rate:

        rate = 1 / (4 + k)

    where k is the state's church tax rate as a decimal fraction (0.08 for
    Bayern/Baden-Württemberg, 0.09 elsewhere) — per §32d Abs. 1 Satz 3
    EStG (the full statutory formula also nets out creditable foreign
    withholding tax, which this MVP does not model; that term is 0 here).
    At k=0.09 this gives ~24.45%; at k=0.08, ~24.51%.

    Args:
        taxable_capital_income_cents: capital income AFTER the
            Sparer-Pauschbetrag (output of apply_sparer_pauschbetrag).
        church_tax_type: NONE uses the flat 25% rate; anything else uses
            the reduced rate.
        residence_state: determines which state's church tax rate (8% vs
            9%) feeds the reduced-rate formula.
        tax_year: which year's base rate to apply.

    Returns:
        KapESt owed, in cents, floored to the nearest whole Euro.

    Raises:
        InvalidIncomeError: if taxable_capital_income_cents is negative.
    """
    if taxable_capital_income_cents < 0:
        raise InvalidIncomeError("taxable_capital_income_cents cannot be negative.")

    constants = get_constants_for_year(tax_year)

    if church_tax_type == ChurchTaxType.NONE:
        rate = constants.kapitalertragsteuer_rate
    else:
        church_rate = (
            constants.church_tax_rate_bavaria_bw
            if residence_state in LOW_CHURCH_TAX_RATE_STATES
            else constants.church_tax_rate_other_states
        )
        rate = Decimal(1) / (Decimal(4) + church_rate)

    income_euro = Decimal(taxable_capital_income_cents) / _CENTS_PER_EURO
    tax_euro = (income_euro * rate).quantize(Decimal("1"), rounding=ROUND_DOWN)

    return max(int(tax_euro) * 100, 0)


@dataclass(frozen=True)
class CapitalGainsGuenstigerpruefungResult:
    """The outcome of comparing flat Abgeltungsteuer vs. folding capital
    income into the progressive tariff (§32d Abs. 6 EStG)."""

    progressive_tariff_elected: bool
    income_tax_cents: int  # the income-tax component to actually use going forward
    capital_gains_tax_cents: int  # the Abgeltungsteuer component to actually use (0 if elected)


def apply_capital_gains_guenstigerpruefung(
    taxable_income_without_capital_gains_cents: int,
    taxable_capital_income_cents: int,
    income_tax_without_capital_gains_cents: int,
    flat_capital_gains_tax_cents: int,
    is_joint_assessment: bool,
    tax_year: int = 2024,
) -> CapitalGainsGuenstigerpruefungResult:
    """Run the automatic §32d Abs. 6 Günstigerprüfung and return whichever
    treatment produces the lower COMBINED (income tax + capital gains tax)
    total -- the taxpayer never has to apply for this, the Finanzamt keeps
    the cheaper outcome automatically, exactly like the Kinderfreibetrag
    comparison in kinderfreibetrag.py.

    Args:
        taxable_income_without_capital_gains_cents: zu versteuerndes
            Einkommen from regular (non-capital) income only -- the normal
            output of core.calculate_taxable_income (see module docstring
            for why this is the pre-Kinderfreibetrag figure specifically).
        taxable_capital_income_cents: capital income AFTER the
            Sparer-Pauschbetrag (output of apply_sparer_pauschbetrag) --
            the allowance applies regardless of which tariff wins.
        income_tax_without_capital_gains_cents: the ALREADY-COMPUTED
            income tax on regular income alone (post-Kinderfreibetrag/
            tax-credit adjustments) -- kept as the flat path's income-tax
            component if the flat path wins.
        flat_capital_gains_tax_cents: the ALREADY-COMPUTED Abgeltungsteuer
            (output of calculate_kapitalertragsteuer) -- the flat path's
            other component.
        is_joint_assessment: mirrors `users.is_joint_assessment`.
        tax_year: which year's tariff to apply.

    Returns:
        A CapitalGainsGuenstigerpruefungResult carrying the winning
        income_tax_cents/capital_gains_tax_cents to use for the rest of
        the pipeline (Soli/Kirchensteuer should be computed from these,
        not from the original flat-path figures, once this has run).

    Raises:
        InvalidIncomeError: on any negative input.
    """
    for label, value in (
        ("taxable_income_without_capital_gains_cents", taxable_income_without_capital_gains_cents),
        ("taxable_capital_income_cents", taxable_capital_income_cents),
        ("income_tax_without_capital_gains_cents", income_tax_without_capital_gains_cents),
        ("flat_capital_gains_tax_cents", flat_capital_gains_tax_cents),
    ):
        if value < 0:
            raise InvalidIncomeError(f"{label} cannot be negative.")

    combined_zve_cents = taxable_income_without_capital_gains_cents + taxable_capital_income_cents
    income_tax_with_capital_gains_folded_in_cents = calculate_income_tax_for_assessment(
        combined_zve_cents, tax_year, is_joint_assessment
    )

    flat_total_cents = income_tax_without_capital_gains_cents + flat_capital_gains_tax_cents

    if income_tax_with_capital_gains_folded_in_cents < flat_total_cents:
        return CapitalGainsGuenstigerpruefungResult(
            progressive_tariff_elected=True,
            income_tax_cents=income_tax_with_capital_gains_folded_in_cents,
            capital_gains_tax_cents=0,
        )

    return CapitalGainsGuenstigerpruefungResult(
        progressive_tariff_elected=False,
        income_tax_cents=income_tax_without_capital_gains_cents,
        capital_gains_tax_cents=flat_capital_gains_tax_cents,
    )
