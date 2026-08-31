"""
2024 constants (see tax_engine/constants.py): Altersvorsorge Höchstbetrag
€27,565 single / €55,130 joint at 100% deductibility; sonstige
Vorsorgeaufwendungen Höchstbetrag €1,900 single / €3,800 joint, with
Basiskranken-/Pflegepflichtversicherung always fully deductible regardless
of that cap (§10 Abs. 4 EStG).
"""

import pytest

from app.tax_engine.deductions.errors import DeductionValidationError
from app.tax_engine.deductions.vorsorgeaufwand import (
    calculate_altersvorsorge_deduction,
    calculate_sonstige_vorsorgeaufwendungen_deduction,
)


class TestAltersvorsorgeUnderCap:
    def test_single_under_cap_is_fully_deductible(self):
        assert calculate_altersvorsorge_deduction(5_000_00, is_joint_assessment=False) == 5_000_00

    def test_joint_under_cap_is_fully_deductible(self):
        assert calculate_altersvorsorge_deduction(40_000_00, is_joint_assessment=True) == 40_000_00

    def test_zero_contribution_is_zero(self):
        assert calculate_altersvorsorge_deduction(0, is_joint_assessment=False) == 0


class TestAltersvorsorgeCapping:
    def test_single_above_cap_is_capped_at_hoechstbetrag(self):
        assert calculate_altersvorsorge_deduction(30_000_00, is_joint_assessment=False) == 27_565_00

    def test_joint_above_cap_is_capped_at_doubled_hoechstbetrag(self):
        assert calculate_altersvorsorge_deduction(60_000_00, is_joint_assessment=True) == 55_130_00

    def test_joint_cap_is_exactly_double_the_single_cap(self):
        single = calculate_altersvorsorge_deduction(999_999_00, is_joint_assessment=False)
        joint = calculate_altersvorsorge_deduction(999_999_00, is_joint_assessment=True)
        assert joint == single * 2


class TestAltersvorsorgeInputValidation:
    def test_rejects_negative_contribution(self):
        with pytest.raises(DeductionValidationError):
            calculate_altersvorsorge_deduction(-1, is_joint_assessment=False)

    def test_rejects_unsupported_tax_year(self):
        with pytest.raises(ValueError):
            calculate_altersvorsorge_deduction(1_000_00, is_joint_assessment=False, tax_year=1999)


class TestSonstigeVorsorgeaufwendungenBasisabsicherungFloor:
    """Basiskranken-/Pflegepflichtversicherung is always fully deductible,
    even when it exceeds the Höchstbetrag -- the near-universal real case
    for anyone with statutory health insurance, and the whole reason this
    isn't a plain min() against the cap."""

    def test_basisabsicherung_above_cap_is_never_reduced(self):
        # 4,000 + 500 = 4,500 EUR Basisabsicherung, well above the 1,900
        # EUR single cap -- the floor wins regardless of the cap.
        result = calculate_sonstige_vorsorgeaufwendungen_deduction(
            health_insurance_employee_cents=4_000_00,
            long_term_care_insurance_employee_cents=500_00,
            unemployment_insurance_employee_cents=300_00,
            is_joint_assessment=False,
        )
        assert result == 4_500_00

    def test_joint_basisabsicherung_above_cap_is_never_reduced(self):
        result = calculate_sonstige_vorsorgeaufwendungen_deduction(
            health_insurance_employee_cents=4_000_00,
            long_term_care_insurance_employee_cents=500_00,
            unemployment_insurance_employee_cents=300_00,
            is_joint_assessment=True,
        )
        assert result == 4_500_00


class TestSonstigeVorsorgeaufwendungenCapping:
    def test_low_basisabsicherung_plus_unemployment_is_capped(self):
        # 1,000 + 200 = 1,200 EUR Basisabsicherung (below the 1,900 EUR
        # cap), plus 1,000 EUR unemployment insurance -> combined 2,200 EUR
        # is capped down to 1,900 EUR, which still exceeds the 1,200 EUR
        # floor, so the capped total wins.
        result = calculate_sonstige_vorsorgeaufwendungen_deduction(
            health_insurance_employee_cents=1_000_00,
            long_term_care_insurance_employee_cents=200_00,
            unemployment_insurance_employee_cents=1_000_00,
            is_joint_assessment=False,
        )
        assert result == 1_900_00

    def test_low_basisabsicherung_alone_under_cap_is_uncapped(self):
        # 1,000 + 200 = 1,200 EUR combined, no unemployment insurance --
        # under the cap entirely, so the actual total applies.
        result = calculate_sonstige_vorsorgeaufwendungen_deduction(
            health_insurance_employee_cents=1_000_00,
            long_term_care_insurance_employee_cents=200_00,
            unemployment_insurance_employee_cents=0,
            is_joint_assessment=False,
        )
        assert result == 1_200_00

    def test_zero_contributions_is_zero(self):
        result = calculate_sonstige_vorsorgeaufwendungen_deduction(0, 0, 0, is_joint_assessment=False)
        assert result == 0


class TestSonstigeVorsorgeaufwendungenInputValidation:
    def test_rejects_negative_health_insurance(self):
        with pytest.raises(DeductionValidationError):
            calculate_sonstige_vorsorgeaufwendungen_deduction(-1, 0, 0, is_joint_assessment=False)

    def test_rejects_negative_long_term_care_insurance(self):
        with pytest.raises(DeductionValidationError):
            calculate_sonstige_vorsorgeaufwendungen_deduction(0, -1, 0, is_joint_assessment=False)

    def test_rejects_negative_unemployment_insurance(self):
        with pytest.raises(DeductionValidationError):
            calculate_sonstige_vorsorgeaufwendungen_deduction(0, 0, -1, is_joint_assessment=False)

    def test_rejects_unsupported_tax_year(self):
        with pytest.raises(ValueError):
            calculate_sonstige_vorsorgeaufwendungen_deduction(
                0, 0, 0, is_joint_assessment=False, tax_year=1999
            )
