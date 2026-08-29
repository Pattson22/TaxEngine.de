"""
Reference values hand-derived from the 20%-cap formula already verified in
test_donations.py, chained across three simulated years:

Year 1: gesamtbetrag=50,000 EUR (cap=10,000 EUR), donated=15,000 EUR, no
    carry-forward in.
    total_available = 15,000; deductible = min(15,000, 10,000) = 10,000
    carryforward_out = 5,000

Year 2: gesamtbetrag=50,000 EUR (cap=10,000 EUR), donated=3,000 EUR,
    carryforward_in = 5,000 (from Year 1).
    total_available = 8,000; deductible = min(8,000, 10,000) = 8,000
    carryforward_out = 0

Year 3: gesamtbetrag=20,000 EUR (cap=4,000 EUR), donated=0 EUR,
    carryforward_in = 12,000 (a large unused balance from some prior year).
    total_available = 12,000; deductible = min(12,000, 4,000) = 4,000
    carryforward_out = 8,000
"""

import pytest

from app.tax_engine.deductions.donations import (
    SpendenvortragResult,
    calculate_spenden_deduction_with_carryforward,
)
from app.tax_engine.deductions.errors import DeductionValidationError


class TestNoCarryforwardBehavesLikePlainDonation:
    def test_matches_plain_calculation_when_carryforward_is_zero(self):
        result = calculate_spenden_deduction_with_carryforward(
            amount_donated_this_year_cents=1_000_00,
            carryforward_in_cents=0,
            gesamtbetrag_der_einkuenfte_cents=50_000_00,
        )
        assert result == SpendenvortragResult(deductible_this_year_cents=1_000_00, carryforward_out_cents=0)

    def test_zero_donation_and_zero_carryforward_is_zero(self):
        result = calculate_spenden_deduction_with_carryforward(0, 0, 50_000_00)
        assert result == SpendenvortragResult(0, 0)


class TestThreeYearChain:
    def test_year_one_exceeds_cap_and_creates_a_carryforward(self):
        year1 = calculate_spenden_deduction_with_carryforward(
            amount_donated_this_year_cents=15_000_00,
            carryforward_in_cents=0,
            gesamtbetrag_der_einkuenfte_cents=50_000_00,
        )
        assert year1.deductible_this_year_cents == 10_000_00
        assert year1.carryforward_out_cents == 5_000_00

        year2 = calculate_spenden_deduction_with_carryforward(
            amount_donated_this_year_cents=3_000_00,
            carryforward_in_cents=year1.carryforward_out_cents,
            gesamtbetrag_der_einkuenfte_cents=50_000_00,
        )
        assert year2.deductible_this_year_cents == 8_000_00
        assert year2.carryforward_out_cents == 0

    def test_large_carryforward_alone_can_still_exceed_a_lower_cap(self):
        year3 = calculate_spenden_deduction_with_carryforward(
            amount_donated_this_year_cents=0,
            carryforward_in_cents=12_000_00,
            gesamtbetrag_der_einkuenfte_cents=20_000_00,
        )
        assert year3.deductible_this_year_cents == 4_000_00
        assert year3.carryforward_out_cents == 8_000_00


class TestConservationOfTotalAmount:
    def test_deductible_plus_carryforward_out_always_equals_total_available(self):
        for donated, carry_in, income in (
            (5_000_00, 2_000_00, 30_000_00),
            (0, 500_00, 100_00),
            (100_000_00, 0, 10_000_00),
        ):
            result = calculate_spenden_deduction_with_carryforward(donated, carry_in, income)
            assert result.deductible_this_year_cents + result.carryforward_out_cents == donated + carry_in


class TestInputValidation:
    def test_rejects_negative_donation(self):
        with pytest.raises(DeductionValidationError):
            calculate_spenden_deduction_with_carryforward(-1, 0, 50_000_00)

    def test_rejects_negative_carryforward(self):
        with pytest.raises(DeductionValidationError):
            calculate_spenden_deduction_with_carryforward(0, -1, 50_000_00)

    def test_rejects_negative_income(self):
        with pytest.raises(DeductionValidationError):
            calculate_spenden_deduction_with_carryforward(0, 0, -1)

    def test_rejects_unsupported_tax_year(self):
        # Must donate something nonzero -- with total_available=0 the
        # function short-circuits before ever consulting tax_year.
        with pytest.raises(ValueError):
            calculate_spenden_deduction_with_carryforward(1_000_00, 0, 50_000_00, tax_year=1999)
