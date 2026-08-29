import pytest

from app.tax_engine.core import InvalidIncomeError
from app.tax_engine.self_employment_income import calculate_self_employment_income


class TestPositiveProfit:
    def test_revenue_exceeds_expenses(self):
        assert calculate_self_employment_income(60_000_00, 20_000_00) == 40_000_00

    def test_zero_expenses(self):
        assert calculate_self_employment_income(60_000_00, 0) == 60_000_00

    def test_zero_revenue_and_expenses(self):
        assert calculate_self_employment_income(0, 0) == 0


class TestLoss:
    def test_expenses_exceed_revenue_produces_a_loss(self):
        # First-year freelancer: 5,000 EUR revenue, 12,000 EUR startup
        # costs -> a 7,000 EUR loss, a legitimate non-error result.
        result = calculate_self_employment_income(5_000_00, 12_000_00)
        assert result == -7_000_00
        assert result < 0


class TestInputValidation:
    def test_rejects_negative_revenue(self):
        with pytest.raises(InvalidIncomeError):
            calculate_self_employment_income(-1, 1_000_00)

    def test_rejects_negative_expenses(self):
        with pytest.raises(InvalidIncomeError):
            calculate_self_employment_income(1_000_00, -1)
