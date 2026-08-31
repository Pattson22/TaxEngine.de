"""
§32d Abs. 6 EStG Günstigerprüfung: compares flat Abgeltungsteuer vs.
folding capital income into the progressive tariff, keeping whichever
combined total is lower. Expected values are derived from the same
(separately tested) tax_brackets/capital_gains primitives rather than
hand-rederiving the piecewise bracket formula here.
"""

from app.tax_engine.capital_gains import (
    apply_capital_gains_guenstigerpruefung,
    calculate_kapitalertragsteuer,
)
from app.tax_engine.enums import ChurchTaxType, FederalState
from app.tax_engine.tax_brackets import calculate_income_tax_for_assessment


class TestFlatRateWinsAtHigherIncome:
    def test_high_income_keeps_the_flat_rate(self):
        # At 60,000 EUR of regular income the marginal rate is already
        # well above 25%, so folding capital gains in should never help.
        taxable_income_cents = 60_000_00
        taxable_capital_income_cents = 10_000_00
        income_tax_without_cents = calculate_income_tax_for_assessment(
            taxable_income_cents, 2024, is_joint_assessment=False
        )
        flat_capital_gains_tax_cents = calculate_kapitalertragsteuer(
            taxable_capital_income_cents, ChurchTaxType.NONE, FederalState.BERLIN, 2024
        )

        result = apply_capital_gains_guenstigerpruefung(
            taxable_income_cents,
            taxable_capital_income_cents,
            income_tax_without_cents,
            flat_capital_gains_tax_cents,
            is_joint_assessment=False,
        )

        assert result.progressive_tariff_elected is False
        assert result.income_tax_cents == income_tax_without_cents
        assert result.capital_gains_tax_cents == flat_capital_gains_tax_cents


class TestProgressiveTariffWinsAtLowIncome:
    def test_low_income_elects_the_progressive_tariff(self):
        # Both regular income (5,000) and combined income (5,000 + 3,000 =
        # 8,000) sit below the Grundfreibetrag (11,604 in 2024), so
        # progressive income tax is 0 either way -- strictly better than
        # paying flat 25% Abgeltungsteuer on the capital gains.
        taxable_income_cents = 5_000_00
        taxable_capital_income_cents = 3_000_00
        income_tax_without_cents = calculate_income_tax_for_assessment(
            taxable_income_cents, 2024, is_joint_assessment=False
        )
        flat_capital_gains_tax_cents = calculate_kapitalertragsteuer(
            taxable_capital_income_cents, ChurchTaxType.NONE, FederalState.BERLIN, 2024
        )
        assert income_tax_without_cents == 0
        assert flat_capital_gains_tax_cents > 0  # otherwise this test proves nothing

        result = apply_capital_gains_guenstigerpruefung(
            taxable_income_cents,
            taxable_capital_income_cents,
            income_tax_without_cents,
            flat_capital_gains_tax_cents,
            is_joint_assessment=False,
        )

        assert result.progressive_tariff_elected is True
        assert result.income_tax_cents == 0
        assert result.capital_gains_tax_cents == 0


class TestInputValidation:
    def test_rejects_negative_taxable_income(self):
        import pytest

        from app.tax_engine.core import InvalidIncomeError

        with pytest.raises(InvalidIncomeError):
            apply_capital_gains_guenstigerpruefung(-1, 0, 0, 0, is_joint_assessment=False)
