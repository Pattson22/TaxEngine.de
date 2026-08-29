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

Scope limitation: the "Günstigerprüfung" election (§32d Abs. 6 EStG) — a
taxpayer whose personal marginal income tax rate is below 25% can elect to
have capital gains taxed under the regular progressive tariff instead of
the flat Abgeltungsteuer — is NOT implemented. This module always applies
the flat rate, which is the correct (and mandatory, absent an election)
outcome for any filer whose marginal rate is at or above 25%. It is also
NOT the "greater of" comparison pattern from Werbungskosten — since 2009,
individual investment-related costs are not separately deductible at all,
so this is a hard subtraction, not a max().
"""

from __future__ import annotations

from decimal import ROUND_DOWN, Decimal

from app.tax_engine.constants import get_constants_for_year
from app.tax_engine.core import InvalidIncomeError
from app.tax_engine.enums import LOW_CHURCH_TAX_RATE_STATES, ChurchTaxType, FederalState

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
