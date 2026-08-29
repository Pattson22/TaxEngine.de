"""
Reference values hand-computed independently from the Splittingverfahren
definition (§32a Abs. 5 EStG: halve combined zvE, tax the half, double it),
composed with the zone-4 formula already verified in test_tax_brackets.py.

Single filer, zve=200,000 EUR (zone 4): 0.42*200000 - 10602.13 = 73397.87
    -> floor 73,397 EUR
Joint filer, combined zve=200,000 EUR: half = 100,000 EUR (zone 4):
    0.42*100000 - 10602.13 = 31397.87 -> floor 31,397 EUR; doubled = 62,794 EUR
"""

import pytest

from app.tax_engine.tax_brackets import calculate_income_tax, calculate_income_tax_for_assessment


class TestSingleAssessmentDelegation:
    def test_is_joint_assessment_false_matches_plain_calculation(self):
        for zve_eur in (0, 15_604, 66_760, 200_000):
            zve_cents = zve_eur * 100
            assert calculate_income_tax_for_assessment(
                zve_cents, tax_year=2024, is_joint_assessment=False
            ) == calculate_income_tax(zve_cents, tax_year=2024)


class TestSplittingtarifReferenceValues:
    def test_single_filer_reference_value(self):
        assert calculate_income_tax(200_000_00, tax_year=2024) == 73_397_00

    def test_joint_filer_reference_value(self):
        result = calculate_income_tax_for_assessment(
            200_000_00, tax_year=2024, is_joint_assessment=True
        )
        assert result == 62_794_00

    def test_splitting_never_produces_more_tax_than_single_assessment(self):
        # The Splittingverfahren can only help (or be neutral for identical
        # incomes), never hurt, relative to filing the same combined income
        # under the single-taxpayer tariff.
        for zve_eur in (0, 20_000, 50_000, 100_000, 200_000, 500_000):
            zve_cents = zve_eur * 100
            single = calculate_income_tax(zve_cents, tax_year=2024)
            joint = calculate_income_tax_for_assessment(
                zve_cents, tax_year=2024, is_joint_assessment=True
            )
            assert joint <= single

    def test_zero_income_joint_assessment_is_untaxed(self):
        assert calculate_income_tax_for_assessment(0, tax_year=2024, is_joint_assessment=True) == 0

    def test_odd_cent_combined_zve_does_not_raise(self):
        # 1 cent lost to integer floor division is immaterial to the
        # whole-Euro-rounded result -- this just confirms no crash/exception.
        result = calculate_income_tax_for_assessment(
            100_001, tax_year=2024, is_joint_assessment=True
        )
        assert result >= 0

    def test_rejects_unsupported_tax_year(self):
        with pytest.raises(ValueError):
            calculate_income_tax_for_assessment(50_000_00, tax_year=1999, is_joint_assessment=True)
