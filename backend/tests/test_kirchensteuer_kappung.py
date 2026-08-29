"""
Reference values hand-derived from the documented formulas:

Very high earner, NRW (Kappungssatz 4.0%), zvE=10,000,000 EUR:
    income tax (zone 5) = 0.45*10,000,000 - 18,936.88 = 4,481,063.12
        -> floor 4,481,063 EUR
    KiSt standard = 9% * 4,481,063 = 403,295.67 -> floor 403,295 EUR
        (= 4.03% of zvE)
    Kappung cap = 4.0% * 10,000,000 = 400,000 EUR
    403,295 EUR > 400,000 EUR -> CAPPED at 400,000 EUR

Moderate earner, NRW, zvE=100,000 EUR:
    income tax (zone 4) = 0.42*100,000 - 10,602.13 = 31,397.87 -> floor 31,397 EUR
    KiSt standard = 9% * 31,397 = 2,825.73 -> floor 2,825 EUR (= 2.825% of zvE)
    Kappung cap = 4.0% * 100,000 = 4,000 EUR
    2,825 EUR < 4,000 EUR -> NOT capped, stays 2,825 EUR
"""

import pytest

from app.tax_engine.church_tax import (
    apply_kirchensteuer_kappung,
    calculate_kirchensteuer,
    calculate_kirchensteuer_kappung_cap,
)
from app.tax_engine.core import InvalidIncomeError
from app.tax_engine.enums import ChurchTaxType, FederalState
from app.tax_engine.tax_brackets import calculate_income_tax


class TestKappungCapCalculation:
    def test_nrw_cap_reference_value(self):
        assert calculate_kirchensteuer_kappung_cap(10_000_000_00, FederalState.NORDRHEIN_WESTFALEN) == 400_000_00

    def test_bayern_has_no_kappung(self):
        assert calculate_kirchensteuer_kappung_cap(10_000_000_00, FederalState.BAYERN) is None

    def test_zero_income_gives_zero_cap(self):
        assert calculate_kirchensteuer_kappung_cap(0, FederalState.NORDRHEIN_WESTFALEN) == 0

    def test_rejects_negative_income(self):
        with pytest.raises(InvalidIncomeError):
            calculate_kirchensteuer_kappung_cap(-1, FederalState.NORDRHEIN_WESTFALEN)


class TestApplyKappungHighEarner:
    def test_very_high_earner_is_capped(self):
        zve = 10_000_000_00
        tax = calculate_income_tax(zve)
        standard = calculate_kirchensteuer(tax, ChurchTaxType.EVANGELISCH, FederalState.NORDRHEIN_WESTFALEN)
        assert standard == 403_295_00

        capped = apply_kirchensteuer_kappung(standard, zve, FederalState.NORDRHEIN_WESTFALEN)
        assert capped == 400_000_00
        assert capped < standard


class TestApplyKappungModerateEarner:
    def test_moderate_earner_is_not_capped(self):
        zve = 100_000_00
        tax = calculate_income_tax(zve)
        standard = calculate_kirchensteuer(tax, ChurchTaxType.EVANGELISCH, FederalState.NORDRHEIN_WESTFALEN)
        assert standard == 2_825_00

        result = apply_kirchensteuer_kappung(standard, zve, FederalState.NORDRHEIN_WESTFALEN)
        assert result == standard  # unchanged -- the cap never kicks in


class TestBayernNeverCaps:
    def test_even_extreme_income_is_never_capped_in_bayern(self):
        zve = 50_000_000_00
        tax = calculate_income_tax(zve)
        standard = calculate_kirchensteuer(tax, ChurchTaxType.ROEMISCH_KATHOLISCH, FederalState.BAYERN)

        result = apply_kirchensteuer_kappung(standard, zve, FederalState.BAYERN)
        assert result == standard


class TestResultNeverExceedsStandardAmount:
    def test_kappung_can_only_help_never_hurt(self):
        for zve_eur, state in (
            (0, FederalState.NORDRHEIN_WESTFALEN),
            (50_000, FederalState.HESSEN),
            (1_000_000, FederalState.BERLIN),
            (100_000_000, FederalState.SAARLAND),
        ):
            zve_cents = zve_eur * 100
            tax = calculate_income_tax(zve_cents)
            standard = calculate_kirchensteuer(tax, ChurchTaxType.EVANGELISCH, state)
            result = apply_kirchensteuer_kappung(standard, zve_cents, state)
            assert result <= standard


class TestInputValidation:
    def test_rejects_negative_standard_kirchensteuer(self):
        with pytest.raises(InvalidIncomeError):
            apply_kirchensteuer_kappung(-1, 100_000_00, FederalState.NORDRHEIN_WESTFALEN)

    def test_rejects_unsupported_tax_year(self):
        with pytest.raises(ValueError):
            calculate_kirchensteuer_kappung_cap(
                100_000_00, FederalState.NORDRHEIN_WESTFALEN, tax_year=1999
            )
