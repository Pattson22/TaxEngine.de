import pytest

from app.tax_engine.core import (
    DeductionLine,
    InvalidIncomeError,
    apply_pauschbetrag_or_actual,
    apply_sonderausgaben_pauschbetrag,
    calculate_taxable_income,
    calculate_werbungskosten,
)


class TestDeductionLine:
    def test_accepts_nonnegative_amount(self):
        line = DeductionLine(category="COMMUTE", amount_cents=1000)
        assert line.amount_cents == 1000

    def test_accepts_zero_amount(self):
        line = DeductionLine(category="COMMUTE", amount_cents=0)
        assert line.amount_cents == 0

    def test_rejects_negative_amount(self):
        with pytest.raises(InvalidIncomeError):
            DeductionLine(category="COMMUTE", amount_cents=-1)


class TestCalculateWerbungskosten:
    def test_empty_list_returns_zero(self):
        assert calculate_werbungskosten([]) == 0

    def test_sums_single_line(self):
        lines = [DeductionLine("COMMUTE", 132_000)]
        assert calculate_werbungskosten(lines) == 132_000

    def test_sums_multiple_lines_across_categories(self):
        lines = [
            DeductionLine("COMMUTE", 132_000),
            DeductionLine("HOME_OFFICE", 84_000),
            DeductionLine("WORK_EQUIPMENT", 25_000),
        ]
        assert calculate_werbungskosten(lines) == 241_000


class TestApplyPauschbetragOrActual:
    def test_actual_below_pauschbetrag_returns_pauschbetrag(self):
        # 500 EUR of real receipts is below the 1,230 EUR flat rate.
        assert apply_pauschbetrag_or_actual(50_000, tax_year=2024) == 123_000

    def test_actual_above_pauschbetrag_returns_actual(self):
        # 2,000 EUR of real receipts exceeds the flat rate.
        assert apply_pauschbetrag_or_actual(200_000, tax_year=2024) == 200_000

    def test_actual_exactly_equal_to_pauschbetrag(self):
        assert apply_pauschbetrag_or_actual(123_000, tax_year=2024) == 123_000

    def test_zero_real_deductions_returns_pauschbetrag(self):
        assert apply_pauschbetrag_or_actual(0, tax_year=2024) == 123_000

    def test_rejects_negative_real_werbungskosten(self):
        with pytest.raises(InvalidIncomeError):
            apply_pauschbetrag_or_actual(-1, tax_year=2024)

    def test_rejects_unsupported_tax_year(self):
        with pytest.raises(ValueError):
            apply_pauschbetrag_or_actual(50_000, tax_year=1999)


class TestApplySonderausgabenPauschbetrag:
    def test_actual_below_single_pauschbetrag_returns_pauschbetrag(self):
        assert apply_sonderausgaben_pauschbetrag(0, is_joint_assessment=False, tax_year=2024) == 3_600

    def test_actual_below_joint_pauschbetrag_returns_joint_pauschbetrag(self):
        assert apply_sonderausgaben_pauschbetrag(0, is_joint_assessment=True, tax_year=2024) == 7_200

    def test_actual_above_pauschbetrag_returns_actual(self):
        assert (
            apply_sonderausgaben_pauschbetrag(100_000, is_joint_assessment=False, tax_year=2024)
            == 100_000
        )

    def test_joint_pauschbetrag_is_double_single(self):
        constants_year = 2024
        single = apply_sonderausgaben_pauschbetrag(0, False, constants_year)
        joint = apply_sonderausgaben_pauschbetrag(0, True, constants_year)
        assert joint == single * 2

    def test_rejects_negative_real_sonderausgaben(self):
        with pytest.raises(InvalidIncomeError):
            apply_sonderausgaben_pauschbetrag(-1, is_joint_assessment=False, tax_year=2024)

    def test_rejects_unsupported_tax_year(self):
        with pytest.raises(ValueError):
            apply_sonderausgaben_pauschbetrag(0, is_joint_assessment=False, tax_year=1999)


class TestCalculateTaxableIncome:
    def test_basic_subtraction(self):
        # 45,000 EUR gross minus 1,320 EUR Werbungskosten.
        assert calculate_taxable_income(45_000_00, 1_320_00) == 43_680_00

    def test_with_other_deductions(self):
        assert calculate_taxable_income(45_000_00, 1_230_00, other_deductions_cents=500_00) == 43_270_00

    def test_floors_at_zero_when_deductions_exceed_gross(self):
        assert calculate_taxable_income(1_000_00, 5_000_00) == 0

    def test_zero_gross_income(self):
        assert calculate_taxable_income(0, 0) == 0

    def test_rejects_negative_gross_income(self):
        with pytest.raises(InvalidIncomeError):
            calculate_taxable_income(-1, 0)

    def test_rejects_negative_werbungskosten(self):
        with pytest.raises(InvalidIncomeError):
            calculate_taxable_income(1000, -1)

    def test_rejects_negative_other_deductions(self):
        with pytest.raises(InvalidIncomeError):
            calculate_taxable_income(1000, 0, other_deductions_cents=-1)

    def test_positive_other_income_category_adds_to_taxable_income(self):
        # 45,000 EUR wages + 4,000 EUR net rental income, no Werbungskosten.
        assert (
            calculate_taxable_income(45_000_00, 0, other_income_categories_cents=4_000_00)
            == 49_000_00
        )

    def test_negative_other_income_category_offsets_taxable_income(self):
        # A 7,000 EUR rental LOSS legally reduces taxable income below
        # gross wages -- this is the entire point of the signed parameter
        # (§2 Abs. 3 EStG horizontal loss offsetting), not an error.
        assert (
            calculate_taxable_income(45_000_00, 0, other_income_categories_cents=-7_000_00)
            == 38_000_00
        )

    def test_large_rental_loss_can_floor_total_taxable_income_at_zero(self):
        assert (
            calculate_taxable_income(5_000_00, 0, other_income_categories_cents=-20_000_00) == 0
        )
