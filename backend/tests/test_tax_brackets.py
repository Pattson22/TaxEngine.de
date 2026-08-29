"""
Reference values in this file are computed BY HAND from the documented
§32a EStG polynomial coefficients (see tax_brackets.py module docstring),
independently of the implementation, so these tests catch coefficient
transcription errors rather than just re-asserting whatever the code
already produces.

Zone 2 example (zve=15,604 EUR): y = (15604-11604)/10000 = 0.4
    tax = (922.98*0.4 + 1400) * 0.4 = 1769.192 * 0.4 = 707.6768 -> floor 707 EUR

Zone 3 example (zve=27,005 EUR): z = (27005-17005)/10000 = 1.0
    tax = (181.19*1 + 2397)*1 + 1025.38 = 2578.19 + 1025.38 = 3603.57 -> floor 3603 EUR

Zone 4 example (zve=100,000 EUR):
    tax = 0.42*100000 - 10602.13 = 31397.87 -> floor 31397 EUR

Zone 5 example (zve=300,000 EUR):
    tax = 0.45*300000 - 18936.88 = 116063.12 -> floor 116063 EUR
"""

import pytest

from app.tax_engine.core import InvalidIncomeError
from app.tax_engine.tax_brackets import calculate_income_tax


class TestZoneBoundariesAndZeroTax:
    def test_zero_income_is_untaxed(self):
        assert calculate_income_tax(0, tax_year=2024) == 0

    def test_income_at_grundfreibetrag_is_untaxed(self):
        assert calculate_income_tax(11_604_00, tax_year=2024) == 0

    def test_one_euro_above_grundfreibetrag_rounds_down_to_zero(self):
        # Marginal rate just above the Grundfreibetrag is ~14%, so the tax
        # on a single extra euro (~0.14 EUR) rounds DOWN to a whole euro
        # of 0 per the statutory rounding rule -- this is correct, not a bug.
        assert calculate_income_tax(11_605_00, tax_year=2024) == 0

    def test_meaningfully_above_grundfreibetrag_is_taxed(self):
        # zve=11,704 EUR: y=(11704-11604)/10000=0.01
        # tax = (922.98*0.01 + 1400) * 0.01 = 14.092298 -> floor 14 EUR
        assert calculate_income_tax(11_704_00, tax_year=2024) == 14_00


class TestKnownReferenceValues:
    def test_zone2_reference_value(self):
        assert calculate_income_tax(15_604_00, tax_year=2024) == 707_00

    def test_zone3_reference_value(self):
        assert calculate_income_tax(27_005_00, tax_year=2024) == 3_603_00

    def test_zone4_reference_value(self):
        assert calculate_income_tax(100_000_00, tax_year=2024) == 31_397_00

    def test_zone5_reference_value(self):
        assert calculate_income_tax(300_000_00, tax_year=2024) == 116_063_00


class TestMonotonicityAndRounding:
    def test_tax_is_monotonically_nondecreasing_across_all_zones(self):
        sample_points_eur = [
            0, 5_000, 11_604, 11_605, 15_604, 17_005, 27_005,
            66_760, 66_761, 100_000, 277_825, 277_826, 300_000, 1_000_000,
        ]
        taxes = [calculate_income_tax(eur * 100, tax_year=2024) for eur in sample_points_eur]

        for earlier, later in zip(taxes, taxes[1:]):
            assert later >= earlier

    def test_result_is_always_a_whole_euro(self):
        for zve_eur in (1, 12_345, 66_760, 66_761, 300_000):
            tax = calculate_income_tax(zve_eur * 100, tax_year=2024)
            assert tax % 100 == 0

    def test_zone3_to_zone4_boundary_is_approximately_continuous(self):
        tax_at_boundary = calculate_income_tax(66_760_00, tax_year=2024)
        tax_just_above = calculate_income_tax(66_760_00 + 1, tax_year=2024)
        # One cent of extra income cannot swing the euro-rounded result by
        # more than the +/-1 euro rounding slack on each side.
        assert abs(tax_just_above - tax_at_boundary) <= 200


class TestInputValidation:
    def test_rejects_negative_income(self):
        with pytest.raises(InvalidIncomeError):
            calculate_income_tax(-1, tax_year=2024)

    def test_rejects_implausibly_large_income(self):
        with pytest.raises(InvalidIncomeError):
            calculate_income_tax(100_000_001_00, tax_year=2024)

    def test_accepts_plausibility_ceiling_boundary(self):
        # Exactly at the ceiling should NOT raise.
        calculate_income_tax(100_000_000_00, tax_year=2024)

    def test_rejects_unsupported_tax_year(self):
        with pytest.raises(ValueError):
            calculate_income_tax(50_000_00, tax_year=1999)
