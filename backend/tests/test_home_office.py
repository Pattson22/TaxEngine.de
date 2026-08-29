import pytest

from app.tax_engine.deductions.errors import DeductionValidationError
from app.tax_engine.deductions.home_office import calculate_homeoffice_pauschale


class TestBelowCap:
    def test_zero_days_returns_zero(self):
        assert calculate_homeoffice_pauschale(0) == 0

    def test_days_below_cap(self):
        # 100 days * 6.00 EUR/day = 600.00 EUR
        assert calculate_homeoffice_pauschale(100) == 60_000


class TestAtAndAboveCap:
    def test_days_exactly_at_cap(self):
        # 210 days * 6.00 EUR/day = 1,260.00 EUR
        assert calculate_homeoffice_pauschale(210) == 126_000

    def test_days_above_cap_are_clamped_not_rejected(self):
        # 250 claimed days clamp to the 210-day statutory maximum.
        assert calculate_homeoffice_pauschale(250) == 126_000

    def test_clamped_result_never_exceeds_cap_amount(self):
        assert calculate_homeoffice_pauschale(365) == calculate_homeoffice_pauschale(210)


class TestInputValidation:
    def test_rejects_negative_days(self):
        with pytest.raises(DeductionValidationError):
            calculate_homeoffice_pauschale(-1)

    def test_rejects_unsupported_tax_year(self):
        with pytest.raises(ValueError):
            calculate_homeoffice_pauschale(100, tax_year=1999)
