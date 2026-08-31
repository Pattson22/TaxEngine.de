"""
2024 constants (see tax_engine/constants.py): zumutbare Belastung brackets
at €15,340 / €51,130, staged per BFH VI R 75/14 -- each bracket's rate
applies only to the slice of Gesamtbetrag der Einkünfte within it, not to
the whole amount based on a single bracket lookup.
"""

import pytest

from app.tax_engine.deductions.aussergewoehnliche_belastungen import (
    calculate_aussergewoehnliche_belastungen_deduction,
)
from app.tax_engine.deductions.errors import DeductionValidationError


class TestBelowFirstBracket:
    def test_single_no_children_under_bracket_1(self):
        # GdE 10,000 EUR, single, no children: 10,000 * 5% = 500 EUR
        # zumutbare Belastung. 1,000 EUR costs -> 500 EUR deductible.
        result = calculate_aussergewoehnliche_belastungen_deduction(
            total_costs_cents=1_000_00,
            gesamtbetrag_der_einkuenfte_cents=10_000_00,
            is_joint_assessment=False,
            number_of_children=0,
        )
        assert result == 500_00

    def test_costs_below_zumutbare_belastung_is_zero(self):
        result = calculate_aussergewoehnliche_belastungen_deduction(
            total_costs_cents=100_00,
            gesamtbetrag_der_einkuenfte_cents=10_000_00,
            is_joint_assessment=False,
            number_of_children=0,
        )
        assert result == 0


class TestStagedCalculationAcrossBrackets:
    """GdE 40,000 EUR straddles bracket 1 (up to 15,340) and bracket 2
    (15,340-51,130) -- the staged formula applies bracket 1's rate to the
    first 15,340 EUR and bracket 2's rate only to the remaining 24,660
    EUR, NOT bracket 2's rate to the whole 40,000 EUR."""

    def test_single_no_children(self):
        # 15,340 * 5% + 24,660 * 6% = 767 + 1,479.60 = 2,246.60 EUR
        result = calculate_aussergewoehnliche_belastungen_deduction(
            total_costs_cents=5_000_00,
            gesamtbetrag_der_einkuenfte_cents=40_000_00,
            is_joint_assessment=False,
            number_of_children=0,
        )
        assert result == 5_000_00 - 2_246_60

    def test_joint_no_children_has_lower_rate(self):
        # 15,340 * 4% + 24,660 * 5% = 613.60 + 1,233 = 1,846.60 EUR
        result = calculate_aussergewoehnliche_belastungen_deduction(
            total_costs_cents=5_000_00,
            gesamtbetrag_der_einkuenfte_cents=40_000_00,
            is_joint_assessment=True,
            number_of_children=0,
        )
        assert result == 5_000_00 - 1_846_60

    def test_three_or_more_children_has_lowest_rate(self):
        # 15,340 * 1% + 24,660 * 1% = 153.40 + 246.60 = 400.00 EUR
        result = calculate_aussergewoehnliche_belastungen_deduction(
            total_costs_cents=5_000_00,
            gesamtbetrag_der_einkuenfte_cents=40_000_00,
            is_joint_assessment=False,
            number_of_children=3,
        )
        assert result == 5_000_00 - 400_00

    def test_one_or_two_children_column_ignores_marital_status(self):
        single = calculate_aussergewoehnliche_belastungen_deduction(
            total_costs_cents=5_000_00,
            gesamtbetrag_der_einkuenfte_cents=40_000_00,
            is_joint_assessment=False,
            number_of_children=1,
        )
        joint = calculate_aussergewoehnliche_belastungen_deduction(
            total_costs_cents=5_000_00,
            gesamtbetrag_der_einkuenfte_cents=40_000_00,
            is_joint_assessment=True,
            number_of_children=2,
        )
        assert single == joint


class TestAboveSecondBracket:
    def test_single_no_children_above_bracket_2(self):
        # 15,340*5% + 35,790*6% + 887,000/100... compute directly:
        # slice1=15,340 slice2=35,790 slice3=8,870
        # 15,340*.05 + 35,790*.06 + 8,870*.07
        # = 767 + 2,147.40 + 620.90 = 3,535.30 EUR
        result = calculate_aussergewoehnliche_belastungen_deduction(
            total_costs_cents=10_000_00,
            gesamtbetrag_der_einkuenfte_cents=60_000_00,
            is_joint_assessment=False,
            number_of_children=0,
        )
        assert result == 10_000_00 - 3_535_30


class TestInputValidation:
    def test_rejects_negative_costs(self):
        with pytest.raises(DeductionValidationError):
            calculate_aussergewoehnliche_belastungen_deduction(
                total_costs_cents=-1,
                gesamtbetrag_der_einkuenfte_cents=10_000_00,
                is_joint_assessment=False,
                number_of_children=0,
            )

    def test_rejects_negative_gesamtbetrag(self):
        with pytest.raises(DeductionValidationError):
            calculate_aussergewoehnliche_belastungen_deduction(
                total_costs_cents=1_000_00,
                gesamtbetrag_der_einkuenfte_cents=-1,
                is_joint_assessment=False,
                number_of_children=0,
            )

    def test_rejects_negative_children(self):
        with pytest.raises(DeductionValidationError):
            calculate_aussergewoehnliche_belastungen_deduction(
                total_costs_cents=1_000_00,
                gesamtbetrag_der_einkuenfte_cents=10_000_00,
                is_joint_assessment=False,
                number_of_children=-1,
            )

    def test_rejects_unsupported_tax_year(self):
        with pytest.raises(ValueError):
            calculate_aussergewoehnliche_belastungen_deduction(
                total_costs_cents=1_000_00,
                gesamtbetrag_der_einkuenfte_cents=10_000_00,
                is_joint_assessment=False,
                number_of_children=0,
                tax_year=1999,
            )
