"""
§7 Abs. 4 EStG linear AfA rates: 3% for buildings completed 2023+
(Wachstumschancengesetz), 2% for 1925-2022, 2.5% before 1925.
"""

import pytest

from app.tax_engine.afa import calculate_afa_deduction
from app.tax_engine.core import InvalidIncomeError


class TestRateSelection:
    def test_completed_2023_uses_three_percent(self):
        assert calculate_afa_deduction(300_000_00, 2023) == 9_000_00

    def test_completed_after_2023_uses_three_percent(self):
        assert calculate_afa_deduction(300_000_00, 2024) == 9_000_00

    def test_completed_2022_uses_two_percent(self):
        assert calculate_afa_deduction(200_000_00, 2022) == 4_000_00

    def test_completed_1925_uses_two_percent(self):
        assert calculate_afa_deduction(200_000_00, 1925) == 4_000_00

    def test_completed_1924_uses_two_point_five_percent(self):
        assert calculate_afa_deduction(100_000_00, 1924) == 2_500_00

    def test_completed_long_ago_uses_two_point_five_percent(self):
        assert calculate_afa_deduction(100_000_00, 1850) == 2_500_00


class TestInputValidation:
    def test_rejects_negative_cost(self):
        with pytest.raises(InvalidIncomeError):
            calculate_afa_deduction(-1, 2023)

    def test_rejects_implausibly_early_year(self):
        with pytest.raises(InvalidIncomeError):
            calculate_afa_deduction(100_000_00, 1700)

    def test_rejects_implausibly_late_year(self):
        with pytest.raises(InvalidIncomeError):
            calculate_afa_deduction(100_000_00, 2200)

    def test_zero_cost_is_zero(self):
        assert calculate_afa_deduction(0, 2023) == 0
