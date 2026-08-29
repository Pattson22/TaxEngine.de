import pytest

from app.tax_engine.core import InvalidIncomeError
from app.tax_engine.rental_income import calculate_rental_income


class TestPositiveNetIncome:
    def test_income_exceeds_expenses(self):
        # 12,000 EUR rent - 8,000 EUR expenses = 4,000 EUR net income.
        assert calculate_rental_income(12_000_00, 8_000_00) == 4_000_00

    def test_zero_expenses(self):
        assert calculate_rental_income(12_000_00, 0) == 12_000_00

    def test_zero_income_and_expenses(self):
        assert calculate_rental_income(0, 0) == 0


class TestNegativeNetIncome:
    def test_expenses_exceed_income_produces_a_loss(self):
        # 8,000 EUR rent - 15,000 EUR expenses (e.g. a large repair year)
        # = a 7,000 EUR loss. This is a legitimate, non-error result.
        result = calculate_rental_income(8_000_00, 15_000_00)
        assert result == -7_000_00
        assert result < 0


class TestInputValidation:
    def test_rejects_negative_gross_income(self):
        with pytest.raises(InvalidIncomeError):
            calculate_rental_income(-1, 1_000_00)

    def test_rejects_negative_expenses(self):
        with pytest.raises(InvalidIncomeError):
            calculate_rental_income(1_000_00, -1)
