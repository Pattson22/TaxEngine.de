import dataclasses
from decimal import Decimal

import pytest

from app.tax_engine.constants import TAX_YEAR_2022, TAX_YEAR_2023, TAX_YEAR_2024, get_constants_for_year


def test_get_constants_for_year_returns_2024_values():
    constants = get_constants_for_year(2024)

    assert constants is TAX_YEAR_2024
    assert constants.arbeitnehmer_pauschbetrag_cents == 123_000
    assert constants.grundfreibetrag_cents == 11_604_00
    assert constants.commute_rate_cents_per_km_first_20 == 30
    assert constants.commute_rate_cents_per_km_beyond_20 == 38
    assert constants.commute_rate_first_tier_km_threshold == 20
    assert constants.home_office_rate_cents_per_day == 600
    assert constants.home_office_max_days_per_year == 210


def test_get_constants_for_year_returns_2023_values():
    """2023 was the year several reforms landed: full 100% Altersvorsorge
    deductibility, the raised Sparer-Pauschbetrag, the post-reform
    Homeoffice-Pauschale, and the end of Kindergeld's tiered-by-child-count
    structure -- several of these already match 2024 exactly."""
    constants = get_constants_for_year(2023)

    assert constants is TAX_YEAR_2023
    assert constants.grundfreibetrag_cents == 10_908_00
    assert constants.arbeitnehmer_pauschbetrag_cents == 123_000  # same as 2024
    assert constants.bracket_2_threshold_cents == 15_999_00
    assert constants.bracket_3_threshold_cents == 62_809_00
    assert constants.soli_freigrenze_single_cents == 17_543_00
    assert constants.soli_freigrenze_joint_cents == 35_086_00
    assert constants.home_office_rate_cents_per_day == 600  # post-reform, same as 2024
    assert constants.home_office_max_days_per_year == 210
    assert constants.altersvorsorge_deductible_fraction == Decimal("1.00")  # accelerated to 2023
    assert constants.altersvorsorge_hoechstbetrag_single_cents == 26_528_00
    assert constants.sparer_pauschbetrag_single_cents == 100_000  # raised from 2022's 80,100
    assert constants.sparer_pauschbetrag_joint_cents == 200_000
    assert constants.kindergeld_monthly_cents_per_child == 25_000  # tiered structure ended in 2023


def test_get_constants_for_year_returns_2022_values():
    """2022 predates several 2023 reforms -- Altersvorsorge was only 94%
    deductible, the Sparer-Pauschbetrag and Homeoffice-Pauschale were at
    their pre-reform amounts, and Kindergeld was tiered by child count
    (kindergeld_monthly_cents_per_child holds only the 1st/2nd-child rate,
    since this constant is unused by any calculation -- see its
    docstring)."""
    constants = get_constants_for_year(2022)

    assert constants is TAX_YEAR_2022
    assert constants.grundfreibetrag_cents == 10_347_00
    assert constants.arbeitnehmer_pauschbetrag_cents == 120_000
    assert constants.bracket_2_threshold_cents == 14_926_00
    assert constants.bracket_3_threshold_cents == 58_596_00
    assert constants.soli_freigrenze_single_cents == 16_956_00
    assert constants.soli_freigrenze_joint_cents == 33_912_00
    assert constants.home_office_rate_cents_per_day == 500  # pre-reform
    assert constants.home_office_max_days_per_year == 120
    assert constants.altersvorsorge_deductible_fraction == Decimal("0.94")  # last pre-2023 phase-in year
    assert constants.altersvorsorge_hoechstbetrag_single_cents == 25_639_00
    assert constants.sparer_pauschbetrag_single_cents == 80_100  # pre-2023 amount
    assert constants.sparer_pauschbetrag_joint_cents == 160_200
    assert constants.kindergeld_monthly_cents_per_child == 21_900


def test_2022_2023_2024_share_stable_unindexed_values():
    """A handful of figures haven't changed across all three years -- worth
    asserting explicitly so a future edit that accidentally diverges one of
    them gets caught."""
    for year in (TAX_YEAR_2022, TAX_YEAR_2023, TAX_YEAR_2024):
        assert year.sonderausgaben_pauschbetrag_single_cents == 3_600
        assert year.sonderausgaben_pauschbetrag_joint_cents == 7_200
        assert year.sonstige_vorsorgeaufwendungen_hoechstbetrag_single_cents == 190_000
        assert year.sonstige_vorsorgeaufwendungen_hoechstbetrag_joint_cents == 380_000
        assert year.handwerkerleistungen_credit_fraction == Decimal("0.20")
        assert year.handwerkerleistungen_max_credit_cents == 120_000
        assert year.kapitalertragsteuer_rate == Decimal("0.25")
        assert year.zumutbare_belastung_bracket_1_threshold_cents == 15_340_00
        assert year.zumutbare_belastung_bracket_2_threshold_cents == 51_130_00


def test_get_constants_for_year_rejects_unsupported_year():
    with pytest.raises(ValueError, match="No verified tax constants"):
        get_constants_for_year(1999)


def test_get_constants_for_year_rejects_future_unpublished_year():
    with pytest.raises(ValueError):
        get_constants_for_year(2030)


def test_tax_year_constants_is_immutable():
    constants = get_constants_for_year(2024)

    with pytest.raises(dataclasses.FrozenInstanceError):
        constants.arbeitnehmer_pauschbetrag_cents = 0
