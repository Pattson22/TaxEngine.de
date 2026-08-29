import pytest

from app.tax_engine.deductions.errors import DeductionValidationError
from app.tax_engine.tax_credits import apply_tax_credit
from app.tax_engine.tax_credits.handwerkerleistungen import calculate_handwerkerleistungen_credit


class TestUnderCap:
    def test_zero_labor_cost_returns_zero(self):
        assert calculate_handwerkerleistungen_credit(0) == 0

    def test_20_percent_of_labor_cost_below_cap(self):
        # 2,000 EUR labor cost * 20% = 400 EUR, well under the 1,200 EUR cap.
        assert calculate_handwerkerleistungen_credit(2_000_00) == 400_00


class TestCapping:
    def test_credit_exactly_at_cap(self):
        # 6,000 EUR labor cost * 20% = 1,200 EUR = exactly the cap.
        assert calculate_handwerkerleistungen_credit(6_000_00) == 1_200_00

    def test_credit_above_cap_is_capped(self):
        # 20,000 EUR labor cost * 20% = 4,000 EUR, capped down to 1,200 EUR.
        assert calculate_handwerkerleistungen_credit(20_000_00) == 1_200_00


class TestInputValidation:
    def test_rejects_negative_labor_cost(self):
        with pytest.raises(DeductionValidationError):
            calculate_handwerkerleistungen_credit(-1)

    def test_rejects_unsupported_tax_year(self):
        with pytest.raises(ValueError):
            calculate_handwerkerleistungen_credit(1_000_00, tax_year=1999)


class TestApplyTaxCredit:
    def test_credit_reduces_assessed_tax(self):
        assert apply_tax_credit(assessed_tax_cents=10_000_00, credit_cents=1_200_00) == 8_800_00

    def test_credit_floors_at_zero_never_goes_negative(self):
        # A taxpayer with very low tax liability cannot turn a credit into
        # a cash payout via this mechanism.
        assert apply_tax_credit(assessed_tax_cents=500_00, credit_cents=1_200_00) == 0

    def test_zero_credit_leaves_tax_unchanged(self):
        assert apply_tax_credit(assessed_tax_cents=10_000_00, credit_cents=0) == 10_000_00

    def test_rejects_negative_assessed_tax(self):
        with pytest.raises(ValueError):
            apply_tax_credit(assessed_tax_cents=-1, credit_cents=0)

    def test_rejects_negative_credit(self):
        with pytest.raises(ValueError):
            apply_tax_credit(assessed_tax_cents=1_000_00, credit_cents=-1)
