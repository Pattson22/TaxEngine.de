"""
Reference values hand-computed from the §4 SolZG formula documented in
soli.py's module docstring:

    Single Freigrenze = 18,130 EUR; Joint Freigrenze = 36,260 EUR
    Milderungszone: 11.9% * (income_tax - Freigrenze)
    Flat zone: 5.5% * income_tax
    Soli = floor(min(tapered, flat))

income_tax=20,000 EUR (single): tapered = 0.119*(20000-18130) = 0.119*1870
    = 222.53 -> floor 222 EUR
income_tax=30,000 EUR (single): tapered = 0.119*(30000-18130) = 0.119*11870
    = 1412.53 -> floor 1412 EUR (still in Milderungszone, since 30,000 <
    the ~33,710 EUR crossover point)
income_tax=40,000 EUR (single): flat = 0.055*40000 = 2200 EUR; tapered =
    0.119*(40000-18130) = 2602.53 EUR; min = 2200 EUR (flat zone, since
    40,000 > crossover)
income_tax=40,000 EUR (joint): tapered = 0.119*(40000-36260) = 0.119*3740
    = 445.06 -> floor 445 EUR
"""

import pytest

from app.tax_engine.core import InvalidIncomeError
from app.tax_engine.soli import calculate_solidaritaetszuschlag


class TestBelowFreigrenze:
    def test_zero_income_tax_is_untaxed(self):
        assert calculate_solidaritaetszuschlag(0) == 0

    def test_at_single_freigrenze_is_untaxed(self):
        assert calculate_solidaritaetszuschlag(18_130_00, is_joint_assessment=False) == 0

    def test_at_joint_freigrenze_is_untaxed(self):
        assert calculate_solidaritaetszuschlag(36_260_00, is_joint_assessment=True) == 0

    def test_just_below_single_freigrenze_is_untaxed(self):
        assert calculate_solidaritaetszuschlag(18_129_00, is_joint_assessment=False) == 0


class TestMilderungszoneReferenceValues:
    def test_single_20000_income_tax(self):
        assert calculate_solidaritaetszuschlag(20_000_00, is_joint_assessment=False) == 222_00

    def test_single_30000_income_tax(self):
        assert calculate_solidaritaetszuschlag(30_000_00, is_joint_assessment=False) == 1_412_00

    def test_joint_40000_income_tax(self):
        assert calculate_solidaritaetszuschlag(40_000_00, is_joint_assessment=True) == 445_00


class TestFlatZoneReferenceValue:
    def test_single_40000_income_tax_uses_flat_rate(self):
        assert calculate_solidaritaetszuschlag(40_000_00, is_joint_assessment=False) == 2_200_00

    def test_high_income_never_exceeds_flat_5_5_percent(self):
        # At very high income tax, Soli must converge on exactly 5.5%.
        income_tax_cents = 1_000_000_00
        soli = calculate_solidaritaetszuschlag(income_tax_cents, is_joint_assessment=False)
        assert soli == 55_000_00


class TestMonotonicity:
    def test_soli_is_monotonically_nondecreasing(self):
        sample_points_eur = [0, 10_000, 18_130, 18_131, 20_000, 30_000, 40_000, 100_000]
        values = [
            calculate_solidaritaetszuschlag(eur * 100, is_joint_assessment=False)
            for eur in sample_points_eur
        ]
        for earlier, later in zip(values, values[1:]):
            assert later >= earlier


class TestInputValidation:
    def test_rejects_negative_income_tax(self):
        with pytest.raises(InvalidIncomeError):
            calculate_solidaritaetszuschlag(-1)

    def test_rejects_unsupported_tax_year(self):
        with pytest.raises(ValueError):
            calculate_solidaritaetszuschlag(50_000_00, tax_year=1999)
