"""
2024 rule: 2/3 of costs (approximated by the constant 0.6667), capped at
€4,000 per child.

3,000 EUR costs, 1 child: 3000 * 0.6667 = 2000.1 -> floor 2,000 EUR (under cap)
10,000 EUR costs, 1 child: 10000 * 0.6667 = 6,667.0 -> floor 6,667 EUR,
    capped down to the 4,000 EUR/child ceiling
10,000 EUR costs, 2 children: same 6,667 EUR fraction, but the aggregate
    cap is now 2*4,000 = 8,000 EUR, so the fraction (6,667 EUR) applies
    uncapped.
"""

import pytest

from app.tax_engine.deductions.childcare import calculate_childcare_deduction
from app.tax_engine.deductions.errors import DeductionValidationError


class TestUnderCap:
    def test_costs_under_per_child_cap(self):
        assert calculate_childcare_deduction(3_000_00, number_of_children=1) == 2_000_00

    def test_zero_costs_returns_zero(self):
        assert calculate_childcare_deduction(0, number_of_children=1) == 0


class TestCapping:
    def test_single_child_cost_above_cap_is_capped(self):
        assert calculate_childcare_deduction(10_000_00, number_of_children=1) == 4_000_00

    def test_same_cost_with_two_children_is_not_capped(self):
        assert calculate_childcare_deduction(10_000_00, number_of_children=2) == 6_667_00

    def test_aggregate_cap_scales_with_child_count(self):
        # 3 children -> 12,000 EUR cap, well above the fractional amount.
        # 15000 * 0.6667 = 10000.5 -> floor 10,000 EUR = 1,000,000 cents.
        result = calculate_childcare_deduction(15_000_00, number_of_children=3)
        assert result == 10_000_00
        assert result < 3 * 4_000_00


class TestInputValidation:
    def test_rejects_negative_costs(self):
        with pytest.raises(DeductionValidationError):
            calculate_childcare_deduction(-1, number_of_children=1)

    def test_rejects_negative_child_count(self):
        with pytest.raises(DeductionValidationError):
            calculate_childcare_deduction(1_000_00, number_of_children=-1)

    def test_rejects_positive_costs_with_zero_children(self):
        with pytest.raises(DeductionValidationError):
            calculate_childcare_deduction(1_000_00, number_of_children=0)

    def test_zero_costs_with_zero_children_is_allowed(self):
        assert calculate_childcare_deduction(0, number_of_children=0) == 0

    def test_rejects_unsupported_tax_year(self):
        with pytest.raises(ValueError):
            calculate_childcare_deduction(1_000_00, number_of_children=1, tax_year=1999)
