import dataclasses

import pytest

from app.tax_engine.constants import TAX_YEAR_2024, get_constants_for_year


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
