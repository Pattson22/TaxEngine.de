"""
Bridges persisted DB rows (User, WageTaxCertificate, Deduction) into
`app.tax_engine`'s plain-int/dataclass inputs, and writes the results back
onto a TaxFiling row. This is the ONLY place in the codebase that does
that translation — API routes stay thin (load user, call this, return the
result), and `app.tax_engine` itself stays completely framework/DB-free
(see its package docstring).
"""

from __future__ import annotations

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.capital_income_statement import CapitalIncomeStatement
from app.models.deduction import Deduction
from app.models.enums import DeductionCategory, FilingStatus
from app.models.rental_property_statement import RentalPropertyStatement
from app.models.self_employment_statement import SelfEmploymentStatement
from app.models.tax_filing import TaxFiling
from app.models.user import User
from app.models.wage_tax_certificate import WageTaxCertificate
from app.schemas.deduction import (
    ChildcareDetails,
    CommuteDetails,
    DonationDetails,
    HandwerkerleistungenDetails,
    HomeOfficeDetails,
)
from app.tax_engine.capital_gains import apply_sparer_pauschbetrag, calculate_kapitalertragsteuer
from app.tax_engine.church_tax import apply_kirchensteuer_kappung, calculate_kirchensteuer
from app.tax_engine.core import (
    DeductionLine,
    apply_pauschbetrag_or_actual,
    apply_sonderausgaben_pauschbetrag,
    calculate_taxable_income,
    calculate_werbungskosten,
)
from app.tax_engine.deductions.childcare import calculate_childcare_deduction
from app.tax_engine.deductions.commute import calculate_entfernungspauschale
from app.tax_engine.deductions.donations import calculate_spenden_deduction_with_carryforward
from app.tax_engine.deductions.home_office import calculate_homeoffice_pauschale
from app.tax_engine.kinderfreibetrag import apply_kinderfreibetrag_guenstigerpruefung
from app.tax_engine.rental_income import calculate_rental_income
from app.tax_engine.self_employment_income import calculate_self_employment_income
from app.tax_engine.soli import (
    calculate_solidaritaetszuschlag,
    calculate_solidaritaetszuschlag_on_capital_gains_tax,
)
from app.tax_engine.tax_credits import apply_tax_credit
from app.tax_engine.tax_credits.handwerkerleistungen import calculate_handwerkerleistungen_credit


class TaxCalculationError(ValueError):
    """A deduction's `details` JSONB couldn't be interpreted for its
    category. Pydantic validation on the API's write path should already
    catch most of these — this is a defense-in-depth check so a malformed
    payload fails with a clear message here instead of a raw
    KeyError/TypeError surfacing from inside app.tax_engine."""


# Werbungskosten (§9 EStG, reduce taxable income) vs. Sonderausgaben
# (§10 EStG, their own separate Pauschbetrag) vs. tax CREDITS (§35a EStG,
# subtracted from the final liability, not from taxable income) — see
# docs/TAXFIX_GAP_ANALYSIS.md for why Handwerkerleistungen is a credit.
_WERBUNGSKOSTEN_CATEGORIES = frozenset({
    DeductionCategory.COMMUTE,
    DeductionCategory.HOME_OFFICE,
    DeductionCategory.WORK_EQUIPMENT,
    DeductionCategory.FURTHER_EDUCATION,
    DeductionCategory.DOUBLE_HOUSEHOLD,
    DeductionCategory.OTHER,
})
# DONATIONS is deliberately NOT in this set -- it needs to be aggregated
# across ALL of a user's donation rows and run through ONE combined
# carry-forward calculation (see _aggregate_donations_this_year), not
# resolved per-row like every other category. Putting it in this set would
# check each row against the full 20% cap independently, double-counting
# the allowance across multiple donation entries.
_SONDERAUSGABEN_CATEGORIES = frozenset({
    DeductionCategory.INSURANCE,
    DeductionCategory.CHILDCARE,
})
_CREDIT_CATEGORIES = frozenset({DeductionCategory.HANDWERKERLEISTUNGEN})


def calculate_tax_filing(db: Session, user: User, tax_year: int) -> TaxFiling:
    """Run the full tax_engine pipeline for one user/tax_year and persist
    the result onto that year's TaxFiling row (creating it if needed).

    Does not commit — the caller (API route) owns the transaction boundary.
    """
    filing = (
        db.query(TaxFiling)
        .filter(TaxFiling.user_id == user.id, TaxFiling.tax_year == tax_year)
        .one_or_none()
    )
    if filing is None:
        filing = TaxFiling(user_id=user.id, tax_year=tax_year)
        db.add(filing)
        db.flush()  # assigns filing.id / defaults so number_of_children etc. are readable below

    wage_certs = (
        db.query(WageTaxCertificate)
        .filter(WageTaxCertificate.user_id == user.id, WageTaxCertificate.tax_year == tax_year)
        .all()
    )
    gross_income_cents = sum(c.gross_wage_cents for c in wage_certs)
    total_withheld_cents = sum(
        c.income_tax_withheld_cents + c.solidarity_surcharge_cents + c.church_tax_withheld_cents
        for c in wage_certs
    )

    capital_income_statements = (
        db.query(CapitalIncomeStatement)
        .filter(
            CapitalIncomeStatement.user_id == user.id, CapitalIncomeStatement.tax_year == tax_year
        )
        .all()
    )
    gross_capital_income_cents = sum(s.gross_income_cents for s in capital_income_statements)
    capital_income_withheld_cents = sum(
        s.kapitalertragsteuer_withheld_cents
        + s.solidarity_surcharge_withheld_cents
        + s.church_tax_withheld_cents
        for s in capital_income_statements
    )
    total_withheld_cents += capital_income_withheld_cents

    rental_statements = (
        db.query(RentalPropertyStatement)
        .filter(
            RentalPropertyStatement.user_id == user.id, RentalPropertyStatement.tax_year == tax_year
        )
        .all()
    )
    # Sum each property's net result (which may itself be negative) rather
    # than summing gross income and expenses separately -- a loss on one
    # property and a gain on another correctly net against each other here,
    # matching how §21 EStG income is assessed per taxpayer, not per property.
    net_rental_income_cents = sum(
        calculate_rental_income(s.gross_rental_income_cents, s.deductible_expenses_cents)
        for s in rental_statements
    )

    self_employment_statements = (
        db.query(SelfEmploymentStatement)
        .filter(
            SelfEmploymentStatement.user_id == user.id, SelfEmploymentStatement.tax_year == tax_year
        )
        .all()
    )
    net_self_employment_income_cents = sum(
        calculate_self_employment_income(s.gross_revenue_cents, s.deductible_expenses_cents)
        for s in self_employment_statements
    )

    # Combined signed contribution from every OTHER progressive-tariff
    # income category (rental + self-employment) -- capital gains is
    # excluded, since it is taxed under the separate Abgeltungsteuer
    # regime and never touches this figure.
    net_other_income_categories_cents = net_rental_income_cents + net_self_employment_income_cents

    deductions = (
        db.query(Deduction)
        .filter(Deduction.user_id == user.id, Deduction.tax_year == tax_year)
        .all()
    )

    werbungskosten_lines: list[DeductionLine] = []
    sonderausgaben_real_cents = 0
    handwerker_credit_cents = 0

    # Gesamtbetrag der Einkünfte for the donation cap (§10b Abs. 1 EStG)
    # sums ALL progressive-tariff income categories (rental +
    # self-employment) -- floored at 0 since a negative total makes a
    # donation cap meaningless and calculate_spenden_deduction rejects
    # negative inputs outright.
    gesamtbetrag_der_einkuenfte_cents = max(
        gross_income_cents + net_other_income_categories_cents, 0
    )

    for deduction in deductions:
        if deduction.category == DeductionCategory.DONATIONS:
            continue  # handled separately below via _aggregate_donations_this_year

        amount_cents = _resolve_deduction_amount_cents(deduction, tax_year)

        if deduction.category in _WERBUNGSKOSTEN_CATEGORIES:
            werbungskosten_lines.append(DeductionLine(deduction.category.value, amount_cents))
        elif deduction.category in _SONDERAUSGABEN_CATEGORIES:
            sonderausgaben_real_cents += amount_cents
        elif deduction.category in _CREDIT_CATEGORIES:
            handwerker_credit_cents += amount_cents
        else:  # pragma: no cover - DONATIONS is skipped above; the three sets exhaust the rest
            raise TaxCalculationError(f"Unhandled deduction category: {deduction.category}")

    prior_year_filing = (
        db.query(TaxFiling)
        .filter(TaxFiling.user_id == user.id, TaxFiling.tax_year == tax_year - 1)
        .one_or_none()
    )
    donation_carryforward_in_cents = (
        prior_year_filing.donation_carryforward_out_cents or 0
    ) if prior_year_filing is not None else 0

    donated_this_year_cents = _aggregate_donations_this_year(deductions)
    spendenvortrag = calculate_spenden_deduction_with_carryforward(
        donated_this_year_cents,
        donation_carryforward_in_cents,
        gesamtbetrag_der_einkuenfte_cents,
        tax_year,
    )
    sonderausgaben_real_cents += spendenvortrag.deductible_this_year_cents

    werbungskosten_real_cents = calculate_werbungskosten(werbungskosten_lines)
    werbungskosten_applied_cents = apply_pauschbetrag_or_actual(werbungskosten_real_cents, tax_year)
    sonderausgaben_applied_cents = apply_sonderausgaben_pauschbetrag(
        sonderausgaben_real_cents, user.is_joint_assessment, tax_year
    )

    taxable_income_cents = calculate_taxable_income(
        gross_income_cents,
        werbungskosten_applied_cents,
        sonderausgaben_applied_cents,
        other_income_categories_cents=net_other_income_categories_cents,
    )
    guenstigerpruefung = apply_kinderfreibetrag_guenstigerpruefung(
        taxable_income_cents,
        filing.number_of_children,
        user.is_joint_assessment,
        filing.kindergeld_received_cents,
        tax_year,
    )
    income_tax_cents = guenstigerpruefung.final_income_tax_cents
    income_tax_after_credits_cents = apply_tax_credit(income_tax_cents, handwerker_credit_cents)

    soli_cents = calculate_solidaritaetszuschlag(
        income_tax_after_credits_cents, user.is_joint_assessment, tax_year
    )
    church_tax_standard_cents = calculate_kirchensteuer(
        income_tax_after_credits_cents, user.church_tax_type, user.residence_state, tax_year
    )
    # Kappung (church tax capping) only applies to the primary Kirchensteuer
    # base (taxable_income_cents); the capital-gains church tax below is
    # left uncapped -- see church_tax.py's module docstring for why the
    # capping mechanism's interaction with Abgeltungsteuer isn't modeled.
    church_tax_cents = apply_kirchensteuer_kappung(
        church_tax_standard_cents, taxable_income_cents, user.residence_state, tax_year
    )

    # Capital gains (Abgeltungsteuer) is computed under a wholly separate
    # flat-rate regime -- see tax_engine/capital_gains.py's module
    # docstring for why it is not folded into the veranlagte Einkommensteuer
    # pipeline above.
    taxable_capital_income_cents = apply_sparer_pauschbetrag(
        gross_capital_income_cents, user.is_joint_assessment, tax_year
    )
    capital_gains_tax_cents = calculate_kapitalertragsteuer(
        taxable_capital_income_cents, user.church_tax_type, user.residence_state, tax_year
    )
    capital_gains_soli_cents = calculate_solidaritaetszuschlag_on_capital_gains_tax(
        capital_gains_tax_cents, tax_year
    )
    capital_gains_church_tax_cents = calculate_kirchensteuer(
        capital_gains_tax_cents, user.church_tax_type, user.residence_state, tax_year
    )

    total_liability_cents = (
        income_tax_after_credits_cents
        + soli_cents
        + church_tax_cents
        + capital_gains_tax_cents
        + capital_gains_soli_cents
        + capital_gains_church_tax_cents
    )
    estimated_refund_cents = total_withheld_cents - total_liability_cents

    filing.taxable_income_cents = taxable_income_cents
    filing.income_tax_cents = income_tax_after_credits_cents
    filing.solidarity_surcharge_cents = soli_cents
    filing.church_tax_cents = church_tax_cents
    filing.tax_credits_applied_cents = handwerker_credit_cents
    filing.kinderfreibetrag_applied = guenstigerpruefung.kinderfreibetrag_applied
    filing.kinderfreibetrag_total_cents = guenstigerpruefung.kinderfreibetrag_total_cents
    filing.capital_gains_tax_cents = capital_gains_tax_cents
    filing.capital_gains_soli_cents = capital_gains_soli_cents
    filing.capital_gains_church_tax_cents = capital_gains_church_tax_cents
    filing.net_rental_income_cents = net_rental_income_cents
    filing.net_self_employment_income_cents = net_self_employment_income_cents
    filing.donation_carryforward_out_cents = spendenvortrag.carryforward_out_cents
    filing.estimated_refund_cents = estimated_refund_cents
    filing.status = FilingStatus.CALCULATED

    db.flush()
    return filing


def _resolve_deduction_amount_cents(deduction: Deduction, tax_year: int) -> int:
    """Turn one Deduction row into a resolved cents amount: dispatch to the
    matching app.tax_engine algorithm for computed categories (recomputing
    from `details` rather than trusting a stored total), or fall back to
    the client-submitted `amount_claimed_cents` for categories with no
    dedicated algorithm yet (see docs/TAXFIX_GAP_ANALYSIS.md).

    DONATIONS is NOT handled here -- see _aggregate_donations_this_year."""
    category = deduction.category

    try:
        if category == DeductionCategory.COMMUTE:
            details = CommuteDetails.model_validate(deduction.details)
            return calculate_entfernungspauschale(details.distance_km, details.days_worked, tax_year)

        if category == DeductionCategory.HOME_OFFICE:
            details = HomeOfficeDetails.model_validate(deduction.details)
            return calculate_homeoffice_pauschale(details.days_claimed, tax_year)

        if category == DeductionCategory.CHILDCARE:
            details = ChildcareDetails.model_validate(deduction.details)
            return calculate_childcare_deduction(
                details.total_costs_cents, details.number_of_children, tax_year
            )

        if category == DeductionCategory.HANDWERKERLEISTUNGEN:
            details = HandwerkerleistungenDetails.model_validate(deduction.details)
            return calculate_handwerkerleistungen_credit(details.labor_cost_cents, tax_year)
    except ValidationError as exc:
        raise TaxCalculationError(
            f"Deduction {deduction.id} (category={category.value}) has an invalid "
            f"`details` payload for that category: {exc}"
        ) from exc

    # WORK_EQUIPMENT, FURTHER_EDUCATION, DOUBLE_HOUSEHOLD, INSURANCE, OTHER:
    # no dedicated app.tax_engine algorithm yet -- trust the client-submitted total.
    return deduction.amount_claimed_cents or 0


def _aggregate_donations_this_year(deductions: list[Deduction]) -> int:
    """Sum `amount_donated_cents` across every DONATIONS-category row for
    the year. Kept separate from _resolve_deduction_amount_cents because
    the 20% cap (and Spendenvortrag carry-forward) applies to the
    COMBINED total across all donation entries, not to each row
    independently -- resolving them one at a time would let each row
    claim the full cap on its own."""
    total_cents = 0
    for deduction in deductions:
        if deduction.category != DeductionCategory.DONATIONS:
            continue
        try:
            details = DonationDetails.model_validate(deduction.details)
        except ValidationError as exc:
            raise TaxCalculationError(
                f"Deduction {deduction.id} (category=DONATIONS) has an invalid "
                f"`details` payload: {exc}"
            ) from exc
        total_cents += details.amount_donated_cents
    return total_cents
