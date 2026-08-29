import pytest

from app.tax_engine.church_tax import calculate_kirchensteuer
from app.tax_engine.core import InvalidIncomeError
from app.tax_engine.enums import ChurchTaxType, FederalState


class TestNoChurchAffiliation:
    def test_none_type_returns_zero_regardless_of_income(self):
        assert calculate_kirchensteuer(
            100_000_00, ChurchTaxType.NONE, FederalState.NORDRHEIN_WESTFALEN
        ) == 0


class TestLowRateStates:
    def test_bayern_uses_8_percent(self):
        # 8% * 10,000 EUR = 800 EUR
        assert calculate_kirchensteuer(
            10_000_00, ChurchTaxType.ROEMISCH_KATHOLISCH, FederalState.BAYERN
        ) == 800_00

    def test_baden_wuerttemberg_uses_8_percent(self):
        assert calculate_kirchensteuer(
            10_000_00, ChurchTaxType.EVANGELISCH, FederalState.BADEN_WUERTTEMBERG
        ) == 800_00


class TestStandardRateStates:
    def test_nordrhein_westfalen_uses_9_percent(self):
        # 9% * 10,000 EUR = 900 EUR
        assert calculate_kirchensteuer(
            10_000_00, ChurchTaxType.EVANGELISCH, FederalState.NORDRHEIN_WESTFALEN
        ) == 900_00

    def test_berlin_uses_9_percent(self):
        assert calculate_kirchensteuer(
            10_000_00, ChurchTaxType.ROEMISCH_KATHOLISCH, FederalState.BERLIN
        ) == 900_00


class TestRounding:
    def test_rounds_down_to_whole_euro(self):
        # 9% * 1,111 EUR = 99.99 EUR -> floors to 99 EUR
        assert calculate_kirchensteuer(
            1_111_00, ChurchTaxType.EVANGELISCH, FederalState.NORDRHEIN_WESTFALEN
        ) == 99_00


class TestInputValidation:
    def test_rejects_negative_income_tax(self):
        with pytest.raises(InvalidIncomeError):
            calculate_kirchensteuer(-1, ChurchTaxType.EVANGELISCH, FederalState.BAYERN)

    def test_zero_income_tax_yields_zero_church_tax(self):
        assert calculate_kirchensteuer(0, ChurchTaxType.EVANGELISCH, FederalState.BAYERN) == 0

    def test_rejects_unsupported_tax_year(self):
        with pytest.raises(ValueError):
            calculate_kirchensteuer(
                10_000_00, ChurchTaxType.EVANGELISCH, FederalState.BAYERN, tax_year=1999
            )
