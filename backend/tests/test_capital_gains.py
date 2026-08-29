"""
Reference values computed from the documented formulas in capital_gains.py
and soli.py's capital-gains function:

    Sparer-Pauschbetrag: €1,000 single / €2,000 joint (§20 Abs. 9 EStG)
    KapESt: 25% flat, or 1/(4+k) when church-tax-liable (k = 0.08 or 0.09)
    Soli on KapESt: flat 5.5%, NO Freigrenze (unlike regular income tax Soli)

taxable=4,000 EUR, EVANGELISCH, NRW (k=0.09):
    rate = 1/4.09 = 0.244499... ; KapESt = floor(4000 * 0.244499) = 977 EUR
taxable=4,000 EUR, ROEMISCH_KATHOLISCH, BAYERN (k=0.08):
    rate = 1/4.08 = 0.245098... ; KapESt = floor(4000 * 0.245098) = 980 EUR
"""

import pytest

from app.tax_engine.capital_gains import apply_sparer_pauschbetrag, calculate_kapitalertragsteuer
from app.tax_engine.church_tax import calculate_kirchensteuer
from app.tax_engine.core import InvalidIncomeError
from app.tax_engine.enums import ChurchTaxType, FederalState
from app.tax_engine.soli import calculate_solidaritaetszuschlag_on_capital_gains_tax


class TestApplySparerPauschbetrag:
    def test_single_below_allowance_is_fully_shielded(self):
        assert apply_sparer_pauschbetrag(500_00, is_joint_assessment=False) == 0

    def test_single_at_exactly_the_allowance(self):
        assert apply_sparer_pauschbetrag(1_000_00, is_joint_assessment=False) == 0

    def test_single_above_allowance(self):
        assert apply_sparer_pauschbetrag(1_500_00, is_joint_assessment=False) == 500_00

    def test_joint_allowance_is_double_single(self):
        assert apply_sparer_pauschbetrag(1_500_00, is_joint_assessment=True) == 0
        assert apply_sparer_pauschbetrag(2_500_00, is_joint_assessment=True) == 500_00

    def test_zero_income_returns_zero(self):
        assert apply_sparer_pauschbetrag(0, is_joint_assessment=False) == 0

    def test_rejects_negative_income(self):
        with pytest.raises(InvalidIncomeError):
            apply_sparer_pauschbetrag(-1, is_joint_assessment=False)

    def test_rejects_unsupported_tax_year(self):
        with pytest.raises(ValueError):
            apply_sparer_pauschbetrag(1_000_00, is_joint_assessment=False, tax_year=1999)


class TestCalculateKapitalertragsteuer:
    def test_no_church_tax_uses_flat_25_percent(self):
        assert (
            calculate_kapitalertragsteuer(4_000_00, ChurchTaxType.NONE, FederalState.BERLIN) == 1_000_00
        )

    def test_zero_taxable_income_returns_zero(self):
        assert calculate_kapitalertragsteuer(0, ChurchTaxType.NONE, FederalState.BERLIN) == 0

    def test_church_tax_9_percent_state_reference_value(self):
        result = calculate_kapitalertragsteuer(
            4_000_00, ChurchTaxType.EVANGELISCH, FederalState.NORDRHEIN_WESTFALEN
        )
        assert result == 977_00

    def test_church_tax_8_percent_state_reference_value(self):
        result = calculate_kapitalertragsteuer(
            4_000_00, ChurchTaxType.ROEMISCH_KATHOLISCH, FederalState.BAYERN
        )
        assert result == 980_00

    def test_church_tax_reduced_rate_is_always_below_25_percent(self):
        no_church = calculate_kapitalertragsteuer(10_000_00, ChurchTaxType.NONE, FederalState.BERLIN)
        with_church = calculate_kapitalertragsteuer(
            10_000_00, ChurchTaxType.EVANGELISCH, FederalState.NORDRHEIN_WESTFALEN
        )
        assert with_church < no_church

    def test_rejects_negative_taxable_income(self):
        with pytest.raises(InvalidIncomeError):
            calculate_kapitalertragsteuer(-1, ChurchTaxType.NONE, FederalState.BERLIN)

    def test_rejects_unsupported_tax_year(self):
        with pytest.raises(ValueError):
            calculate_kapitalertragsteuer(1_000_00, ChurchTaxType.NONE, FederalState.BERLIN, tax_year=1999)


class TestSoliOnCapitalGainsTax:
    def test_flat_5_5_percent(self):
        # 1,000 EUR KapESt * 5.5% = 55 EUR.
        assert calculate_solidaritaetszuschlag_on_capital_gains_tax(1_000_00) == 55_00

    def test_zero_kapest_returns_zero(self):
        assert calculate_solidaritaetszuschlag_on_capital_gains_tax(0) == 0

    def test_no_freigrenze_small_amounts_still_taxed(self):
        # Unlike the regular-income-tax Soli, there is no exemption
        # threshold: even a small KapESt amount owes (rounded) Soli.
        # 20 EUR * 5.5% = 1.10 EUR -> floor 1 EUR.
        assert calculate_solidaritaetszuschlag_on_capital_gains_tax(20_00) == 1_00

    def test_rejects_negative_kapest(self):
        with pytest.raises(InvalidIncomeError):
            calculate_solidaritaetszuschlag_on_capital_gains_tax(-1)

    def test_rejects_unsupported_tax_year(self):
        with pytest.raises(ValueError):
            calculate_solidaritaetszuschlag_on_capital_gains_tax(1_000_00, tax_year=1999)


class TestFullChainComposition:
    def test_composed_pipeline_matches_independently_verified_values(self):
        # 5,000 EUR gross capital income, single, EVANGELISCH, NRW.
        taxable = apply_sparer_pauschbetrag(5_000_00, is_joint_assessment=False)
        assert taxable == 4_000_00

        kapest = calculate_kapitalertragsteuer(
            taxable, ChurchTaxType.EVANGELISCH, FederalState.NORDRHEIN_WESTFALEN
        )
        assert kapest == 977_00

        soli = calculate_solidaritaetszuschlag_on_capital_gains_tax(kapest)
        assert soli == 53_00  # floor(977 * 0.055) = floor(53.735) = 53

        # church_tax.calculate_kirchensteuer is REUSED as-is for the
        # KiSt-on-KapESt line item -- no separate implementation needed.
        church = calculate_kirchensteuer(
            kapest, ChurchTaxType.EVANGELISCH, FederalState.NORDRHEIN_WESTFALEN
        )
        assert church == 87_00  # floor(977 * 0.09) = floor(87.93) = 87
