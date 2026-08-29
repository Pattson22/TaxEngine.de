import pytest

from app.tax_engine.deductions.donations import calculate_spenden_deduction
from app.tax_engine.deductions.errors import DeductionValidationError


class TestUnderCap:
    def test_donation_below_20_percent_cap_is_fully_deductible(self):
        # 1,000 EUR donated, 50,000 EUR total income -> cap is 10,000 EUR,
        # donation is well under it.
        assert calculate_spenden_deduction(1_000_00, 50_000_00) == 1_000_00

    def test_zero_donation_returns_zero(self):
        assert calculate_spenden_deduction(0, 50_000_00) == 0


class TestOverCap:
    def test_donation_above_20_percent_cap_is_capped(self):
        # 20,000 EUR donated, 50,000 EUR total income -> cap is 10,000 EUR.
        assert calculate_spenden_deduction(20_000_00, 50_000_00) == 10_000_00

    def test_donation_exactly_at_cap(self):
        # 10,000 EUR donated, 50,000 EUR total income -> cap is exactly 10,000 EUR.
        assert calculate_spenden_deduction(10_000_00, 50_000_00) == 10_000_00


class TestZeroIncome:
    def test_zero_total_income_means_zero_deductible(self):
        assert calculate_spenden_deduction(500_00, 0) == 0


class TestInputValidation:
    def test_rejects_negative_donation(self):
        with pytest.raises(DeductionValidationError):
            calculate_spenden_deduction(-1, 50_000_00)

    def test_rejects_negative_total_income(self):
        with pytest.raises(DeductionValidationError):
            calculate_spenden_deduction(1_000_00, -1)

    def test_rejects_unsupported_tax_year(self):
        with pytest.raises(ValueError):
            calculate_spenden_deduction(1_000_00, 50_000_00, tax_year=1999)
