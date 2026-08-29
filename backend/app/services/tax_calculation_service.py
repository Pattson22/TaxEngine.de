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

from app.models.deduction import Deduction
from app.models.enums import DeductionCategory, FilingStatus
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
from app.tax_engine.church_tax import calculate_kirchensteuer
from app.tax_engine.core import (
    DeductionLine,
    apply_pauschbetrag_or_actual,
    apply_sonderausgaben_pauschbetrag,
    calculate_taxable_income,
    calculate_werbungskosten,
)
from app.tax_engine.deductions.childcare import calculate_childcare_deduction
from app.tax_engine.deductions.commute import calculate_entfernungspauschale
from app.tax_engine.deductions.donations import calculate_spenden_deduction
from app.tax_engine.deductions.home_office import calculate_homeoffice_pauschale
from app.tax_engine.soli import calculate_solidaritaetszuschlag
from app.tax_engine.tax_brackets import calculate_income_tax_for_assessment
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
_SONDERAUSGABEN_CATEGORIES = frozenset({
    DeductionCategory.INSURANCE,
    DeductionCategory.DONATIONS,
    DeductionCategory.CHILDCARE,
})
_CREDIT_CATEGORIES = frozenset({DeductionCategory.HANDWERKERLEISTUNGEN})


def calculate_tax_filing(db: Session, user: User, tax_year: int) -> TaxFiling:
    """Run the full tax_engine pipeline for one user/tax_year and persist
    the result onto that year's TaxFiling row (creating it if needed).

    Does not commit — the caller (API route) owns the transaction boundary.
    """
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

    deductions = (
        db.query(Deduction)
        .filter(Deduction.user_id == user.id, Deduction.tax_year == tax_year)
        .all()
    )

    werbungskosten_lines: list[DeductionLine] = []
    sonderausgaben_real_cents = 0
    handwerker_credit_cents = 0

    for deduction in deductions:
        amount_cents = _resolve_deduction_amount_cents(deduction, gross_income_cents, tax_year)

        if deduction.category in _WERBUNGSKOSTEN_CATEGORIES:
            werbungskosten_lines.append(DeductionLine(deduction.category.value, amount_cents))
        elif deduction.category in _SONDERAUSGABEN_CATEGORIES:
            sonderausgaben_real_cents += amount_cents
        elif deduction.category in _CREDIT_CATEGORIES:
            handwerker_credit_cents += amount_cents
        else:  # pragma: no cover - the three sets above exhaust DeductionCategory today
            raise TaxCalculationError(f"Unhandled deduction category: {deduction.category}")

    werbungskosten_real_cents = calculate_werbungskosten(werbungskosten_lines)
    werbungskosten_applied_cents = apply_pauschbetrag_or_actual(werbungskosten_real_cents, tax_year)
    sonderausgaben_applied_cents = apply_sonderausgaben_pauschbetrag(
        sonderausgaben_real_cents, user.is_joint_assessment, tax_year
    )

    taxable_income_cents = calculate_taxable_income(
        gross_income_cents, werbungskosten_applied_cents, sonderausgaben_applied_cents
    )
    income_tax_cents = calculate_income_tax_for_assessment(
        taxable_income_cents, tax_year, user.is_joint_assessment
    )
    income_tax_after_credits_cents = apply_tax_credit(income_tax_cents, handwerker_credit_cents)

    soli_cents = calculate_solidaritaetszuschlag(
        income_tax_after_credits_cents, user.is_joint_assessment, tax_year
    )
    church_tax_cents = calculate_kirchensteuer(
        income_tax_after_credits_cents, user.church_tax_type, user.residence_state, tax_year
    )

    total_liability_cents = income_tax_after_credits_cents + soli_cents + church_tax_cents
    estimated_refund_cents = total_withheld_cents - total_liability_cents

    filing = (
        db.query(TaxFiling)
        .filter(TaxFiling.user_id == user.id, TaxFiling.tax_year == tax_year)
        .one_or_none()
    )
    if filing is None:
        filing = TaxFiling(user_id=user.id, tax_year=tax_year)
        db.add(filing)

    filing.taxable_income_cents = taxable_income_cents
    filing.income_tax_cents = income_tax_after_credits_cents
    filing.solidarity_surcharge_cents = soli_cents
    filing.church_tax_cents = church_tax_cents
    filing.tax_credits_applied_cents = handwerker_credit_cents
    filing.estimated_refund_cents = estimated_refund_cents
    filing.status = FilingStatus.CALCULATED

    db.flush()
    return filing


def _resolve_deduction_amount_cents(deduction: Deduction, gross_income_cents: int, tax_year: int) -> int:
    """Turn one Deduction row into a resolved cents amount: dispatch to the
    matching app.tax_engine algorithm for computed categories (recomputing
    from `details` rather than trusting a stored total), or fall back to
    the client-submitted `amount_claimed_cents` for categories with no
    dedicated algorithm yet (see docs/TAXFIX_GAP_ANALYSIS.md)."""
    category = deduction.category

    try:
        if category == DeductionCategory.COMMUTE:
            details = CommuteDetails.model_validate(deduction.details)
            return calculate_entfernungspauschale(details.distance_km, details.days_worked, tax_year)

        if category == DeductionCategory.HOME_OFFICE:
            details = HomeOfficeDetails.model_validate(deduction.details)
            return calculate_homeoffice_pauschale(details.days_claimed, tax_year)

        if category == DeductionCategory.DONATIONS:
            details = DonationDetails.model_validate(deduction.details)
            return calculate_spenden_deduction(details.amount_donated_cents, gross_income_cents, tax_year)

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
