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
from app.tax_engine.afa import calculate_afa_deduction
from app.tax_engine.capital_gains import (
    apply_capital_gains_guenstigerpruefung,
    apply_sparer_pauschbetrag,
    calculate_kapitalertragsteuer,
)
from app.tax_engine.church_tax import apply_kirchensteuer_kappung, calculate_kirchensteuer
from app.tax_engine.constants import SUPPORTED_TAX_YEARS
from app.tax_engine.core import (
    DeductionLine,
    apply_pauschbetrag_or_actual,
    apply_sonderausgaben_pauschbetrag,
    calculate_taxable_income,
    calculate_werbungskosten,
)
from app.tax_engine.deductions.aussergewoehnliche_belastungen import (
    calculate_aussergewoehnliche_belastungen_deduction,
)
from app.tax_engine.deductions.childcare import calculate_childcare_deduction
from app.tax_engine.deductions.commute import calculate_entfernungspauschale
from app.tax_engine.deductions.donations import calculate_spenden_deduction_with_carryforward
from app.tax_engine.deductions.home_office import calculate_homeoffice_pauschale
from app.tax_engine.deductions.vorsorgeaufwand import (
    calculate_altersvorsorge_deduction,
    calculate_sonstige_vorsorgeaufwendungen_deduction,
)
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


def get_supported_tax_years() -> list[int]:
    """Tax years with reviewed, published constants (tax_engine/constants.py),
    sorted ascending. The single source of truth for which years the API
    will accept a filing/calculation for -- both the create-filing
    validation and the frontend's year picker read from this instead of
    hard-coding a year, so a new year only ever needs adding in one place."""
    return sorted(SUPPORTED_TAX_YEARS)


def rental_total_deductible_expenses_cents(statement: RentalPropertyStatement) -> int:
    """One rental property's COMPLETE §9 EStG Werbungskosten figure: the
    filer's own entered expenses plus, when the structured AfA inputs are
    present, the §7 Abs. 4 EStG building depreciation derived from them.

    Shared deliberately by the calculation pipeline (calculate_tax_filing
    below) and by the Anlage V serializer (app/eric/xml_builder.py), which
    must agree exactly: an AfA amount that raises the refund ESTIMATE but
    is missing from the SUBMITTED return would understate the declared
    Werbungskosten, and the assessment would come back lower than the
    estimate promised. That is a real bug this function exists to make
    structurally impossible, so neither caller should re-derive AfA itself.

    AfA is derived on demand rather than persisted onto
    `deductible_expenses_cents`, which is the filer's own input: writing a
    computed value back into an input column would both conflate the two
    and double-count on every recalculation. This matches the project-wide
    rule that computed deductions are recomputed from structured inputs
    rather than trusted as stored totals.
    """
    # BOTH structured fields are required (see RentalPropertyStatement's
    # own docstring) -- with either NULL, the entered expenses are trusted
    # as the complete figure, matching this project's pre-AfA behavior
    # where any depreciation had to be folded in by hand.
    if (
        statement.building_acquisition_cost_cents is not None
        and statement.building_completion_year is not None
    ):
        return statement.deductible_expenses_cents + calculate_afa_deduction(
            statement.building_acquisition_cost_cents, statement.building_completion_year
        )
    return statement.deductible_expenses_cents


def rental_net_income_cents(statement: RentalPropertyStatement) -> int:
    """One rental property's §21 EStG net result -- gross rent minus the
    COMPLETE Werbungskosten figure above, so any derived AfA is included.

    Signed on purpose: a loss here legitimately offsets other income
    (§2 Abs. 3 EStG) and must never be floored at zero. Exposed so the API
    can report the same per-property figure the calculation pipeline uses,
    rather than have each client re-derive it -- a client doing its own
    `gross - deductible_expenses_cents` silently omits AfA and shows the
    filer a number this project disagrees with.
    """
    return calculate_rental_income(
        statement.gross_rental_income_cents, rental_total_deductible_expenses_cents(statement)
    )


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
    DeductionCategory.CHURCH_TAX_PAID,
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
    elif filing.status in (FilingStatus.SUBMITTED, FilingStatus.ACCEPTED, FilingStatus.REJECTED):
        # Amended return, starting here: recalculating a filing that was
        # already submitted means the filer is correcting something and
        # will need to resubmit -- see docs/ELSTER_ERIC_INTEGRATION.md's
        # amendment section for the full design. Clear the stale
        # submission-outcome fields so the frontend's "already submitted"
        # UI doesn't keep showing the OLD Transferticket/acceptance once
        # this filing is ready for a genuinely new one; the full history
        # of every past attempt (including this one) survives regardless
        # in eric_submission_jobs, queryable via GET
        # /tax-filings/{id}/submission-jobs. enqueue_submission() checks
        # that job history (not these fields) to decide is_amendment.
        filing.elster_transfer_ticket = None
        filing.elster_submitted_at = None
        filing.elster_accepted_at = None
        filing.elster_rejection_reason = None

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

    # Vorsorgeaufwendungen (§10 Abs. 1 Nr. 2/3/3a EStG, see
    # tax_engine/deductions/vorsorgeaufwand.py) -- computed from the same
    # employee-side social-insurance contributions employers already report
    # on the electronic Lohnsteuerbescheinigung, summed across every wage
    # certificate for the year exactly like gross_income_cents above.
    pension_insurance_employee_cents = sum(c.pension_insurance_employee_cents for c in wage_certs)
    health_insurance_employee_cents = sum(c.health_insurance_employee_cents for c in wage_certs)
    long_term_care_insurance_employee_cents = sum(
        c.long_term_care_insurance_employee_cents for c in wage_certs
    )
    unemployment_insurance_employee_cents = sum(
        c.unemployment_insurance_employee_cents for c in wage_certs
    )
    altersvorsorge_deduction_cents = calculate_altersvorsorge_deduction(
        pension_insurance_employee_cents, user.is_joint_assessment, tax_year
    )
    sonstige_vorsorgeaufwendungen_deduction_cents = calculate_sonstige_vorsorgeaufwendungen_deduction(
        health_insurance_employee_cents,
        long_term_care_insurance_employee_cents,
        unemployment_insurance_employee_cents,
        user.is_joint_assessment,
        tax_year,
    )
    vorsorgeaufwand_deduction_cents = (
        altersvorsorge_deduction_cents + sonstige_vorsorgeaufwendungen_deduction_cents
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
    net_rental_income_cents = sum(rental_net_income_cents(s) for s in rental_statements)

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
        if deduction.category == DeductionCategory.AUSSERGEWOEHNLICHE_BELASTUNG:
            continue  # handled separately below -- own zumutbare-Belastung threshold, not a per-row resolve

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

    aussergewoehnliche_belastungen_costs_cents = _aggregate_aussergewoehnliche_belastungen_this_year(
        deductions
    )
    aussergewoehnliche_belastungen_deduction_cents = calculate_aussergewoehnliche_belastungen_deduction(
        aussergewoehnliche_belastungen_costs_cents,
        gesamtbetrag_der_einkuenfte_cents,
        user.is_joint_assessment,
        filing.number_of_children,
        tax_year,
    )

    werbungskosten_real_cents = calculate_werbungskosten(werbungskosten_lines)
    werbungskosten_applied_cents = apply_pauschbetrag_or_actual(werbungskosten_real_cents, tax_year)
    sonderausgaben_applied_cents = apply_sonderausgaben_pauschbetrag(
        sonderausgaben_real_cents, user.is_joint_assessment, tax_year
    )

    taxable_income_cents = calculate_taxable_income(
        gross_income_cents,
        werbungskosten_applied_cents,
        sonderausgaben_applied_cents
        + vorsorgeaufwand_deduction_cents
        + aussergewoehnliche_belastungen_deduction_cents,
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

    # Capital gains (Abgeltungsteuer) is computed under a wholly separate
    # flat-rate regime -- see tax_engine/capital_gains.py's module
    # docstring for why it is not folded into the veranlagte Einkommensteuer
    # pipeline above BY DEFAULT. apply_capital_gains_guenstigerpruefung
    # (§32d Abs. 6 EStG) then automatically elects to fold it in anyway
    # when that's cheaper -- this MUST run before soli/church tax below,
    # since both are computed from whichever income_tax figure wins here.
    taxable_capital_income_cents = apply_sparer_pauschbetrag(
        gross_capital_income_cents, user.is_joint_assessment, tax_year
    )
    flat_capital_gains_tax_cents = calculate_kapitalertragsteuer(
        taxable_capital_income_cents, user.church_tax_type, user.residence_state, tax_year
    )
    capital_gains_guenstigerpruefung = apply_capital_gains_guenstigerpruefung(
        taxable_income_cents,
        taxable_capital_income_cents,
        income_tax_after_credits_cents,
        flat_capital_gains_tax_cents,
        user.is_joint_assessment,
        tax_year,
    )
    income_tax_after_credits_cents = capital_gains_guenstigerpruefung.income_tax_cents
    capital_gains_tax_cents = capital_gains_guenstigerpruefung.capital_gains_tax_cents

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
    # Deliberately still keyed on taxable_income_cents (not the combined
    # figure) even when the §32d Abs. 6 election wins, for the same reason
    # -- see capital_gains.py's module docstring's own scope note.
    church_tax_cents = apply_kirchensteuer_kappung(
        church_tax_standard_cents, taxable_income_cents, user.residence_state, tax_year
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
    filing.capital_gains_progressive_election_applied = (
        capital_gains_guenstigerpruefung.progressive_tariff_elected
    )
    filing.net_rental_income_cents = net_rental_income_cents
    filing.net_self_employment_income_cents = net_self_employment_income_cents
    filing.donation_carryforward_out_cents = spendenvortrag.carryforward_out_cents
    filing.altersvorsorge_deduction_cents = altersvorsorge_deduction_cents
    filing.sonstige_vorsorgeaufwendungen_deduction_cents = sonstige_vorsorgeaufwendungen_deduction_cents
    filing.aussergewoehnliche_belastungen_deduction_cents = aussergewoehnliche_belastungen_deduction_cents
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

    DONATIONS and AUSSERGEWOEHNLICHE_BELASTUNG are NOT handled here -- see
    _aggregate_donations_this_year and
    _aggregate_aussergewoehnliche_belastungen_this_year respectively."""
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

    # WORK_EQUIPMENT, FURTHER_EDUCATION, DOUBLE_HOUSEHOLD, INSURANCE,
    # CHURCH_TAX_PAID, OTHER: no dedicated app.tax_engine algorithm --
    # trust the client-submitted total (church tax paid directly has no
    # formula to recompute from structured inputs the way commute/
    # childcare/etc. do; it's a self-reported figure by nature).
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


def _aggregate_aussergewoehnliche_belastungen_this_year(deductions: list[Deduction]) -> int:
    """Sum `amount_claimed_cents` across every AUSSERGEWOEHNLICHE_BELASTUNG
    row for the year -- self-reported like INSURANCE/CHURCH_TAX_PAID/OTHER
    (no dedicated `details` schema), but kept separate from
    _resolve_deduction_amount_cents because the zumutbare Belastung
    threshold (calculate_aussergewoehnliche_belastungen_deduction) applies
    to the COMBINED total across all rows, not to each row independently."""
    return sum(
        deduction.amount_claimed_cents or 0
        for deduction in deductions
        if deduction.category == DeductionCategory.AUSSERGEWOEHNLICHE_BELASTUNG
    )
