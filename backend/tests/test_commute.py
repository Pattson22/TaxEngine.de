import pytest

from app.tax_engine.deductions.commute import calculate_entfernungspauschale
from app.tax_engine.deductions.errors import DeductionValidationError


class TestFirstTierOnly:
    def test_distance_under_20km(self):
        # 10km * 200 days * 0.30 EUR/km = 600.00 EUR
        assert calculate_entfernungspauschale(distance_km=10, days_worked=200) == 60_000

    def test_distance_exactly_20km(self):
        # 20km * 100 days * 0.30 EUR/km = 600.00 EUR
        assert calculate_entfernungspauschale(distance_km=20, days_worked=100) == 60_000


class TestSecondTier:
    def test_distance_beyond_20km_splits_rates(self):
        # First 20km @ 0.30 + 10km @ 0.38 = 6.00 + 3.80 = 9.80 EUR/day
        # 9.80 EUR/day * 200 days = 1,960.00 EUR
        assert calculate_entfernungspauschale(distance_km=30, days_worked=200) == 196_000

    def test_distance_one_km_into_second_tier(self):
        # 20km @ 0.30 + 1km @ 0.38 = 6.00 + 0.38 = 6.38 EUR/day
        assert calculate_entfernungspauschale(distance_km=21, days_worked=1) == 638


class TestZeroCases:
    def test_zero_distance_returns_zero(self):
        assert calculate_entfernungspauschale(distance_km=0, days_worked=200) == 0

    def test_zero_days_returns_zero(self):
        assert calculate_entfernungspauschale(distance_km=20, days_worked=0) == 0


class TestPlausibilityBoundaries:
    def test_max_plausible_distance_is_accepted(self):
        calculate_entfernungspauschale(distance_km=300, days_worked=1)

    def test_distance_beyond_ceiling_is_rejected(self):
        with pytest.raises(DeductionValidationError):
            calculate_entfernungspauschale(distance_km=301, days_worked=1)

    def test_max_plausible_days_is_accepted(self):
        calculate_entfernungspauschale(distance_km=1, days_worked=280)

    def test_days_beyond_ceiling_is_rejected(self):
        with pytest.raises(DeductionValidationError):
            calculate_entfernungspauschale(distance_km=1, days_worked=281)


class TestInputValidation:
    def test_rejects_negative_distance(self):
        with pytest.raises(DeductionValidationError):
            calculate_entfernungspauschale(distance_km=-1, days_worked=100)

    def test_rejects_negative_days(self):
        with pytest.raises(DeductionValidationError):
            calculate_entfernungspauschale(distance_km=10, days_worked=-1)

    def test_rejects_unsupported_tax_year(self):
        with pytest.raises(ValueError):
            calculate_entfernungspauschale(distance_km=10, days_worked=100, tax_year=1999)
