"""
Tests for the /rental-property-statements route's derived-figure mapping.

The route returns AfA, the complete Werbungskosten total, and the net
§21 EStG result alongside the stored columns specifically so no client
re-derives them. The frontend previously computed
`gross_rental_income_cents - deductible_expenses_cents` itself, which
silently EXCLUDES AfA -- showing the filer a net figure the backend's own
refund calculation disagreed with. These lock the mapping in place.

DB-free, matching this suite's convention (see test_tax_filings_route.py).
"""

import uuid
from datetime import datetime, timezone

from app.api.routes.rental_property_statements import _to_read
from app.models.rental_property_statement import RentalPropertyStatement


def _make_statement(**overrides) -> RentalPropertyStatement:
    defaults = dict(
        id=uuid.uuid4(),
        tax_year=2024,
        property_address="Musterstraße 1, Berlin",
        gross_rental_income_cents=1_200_000,
        deductible_expenses_cents=300_000,
        building_acquisition_cost_cents=None,
        building_completion_year=None,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return RentalPropertyStatement(**defaults)


class TestRentalStatementDerivedFigures:
    def test_afa_is_derived_and_netted_off_when_both_inputs_present(self):
        read = _to_read(
            _make_statement(
                building_acquisition_cost_cents=20_000_000,  # 200k EUR building
                building_completion_year=2010,  # 2% linear -> 400_000 cents
            )
        )

        assert read.afa_deduction_cents == 400_000
        assert read.total_deductible_expenses_cents == 700_000
        # Net must reflect the AfA, NOT gross - deductible_expenses_cents.
        assert read.net_rental_income_cents == 500_000
        # The stored column is still reported unchanged alongside it.
        assert read.deductible_expenses_cents == 300_000

    def test_no_afa_without_both_structured_inputs(self):
        for cost, year in [(None, None), (None, 2010), (20_000_000, None)]:
            read = _to_read(
                _make_statement(
                    building_acquisition_cost_cents=cost, building_completion_year=year
                )
            )

            assert read.afa_deduction_cents == 0, (cost, year)
            assert read.total_deductible_expenses_cents == 300_000
            assert read.net_rental_income_cents == 900_000

    def test_net_stays_signed_when_afa_pushes_the_property_into_a_loss(self):
        # A loss legitimately offsets other income (§2 Abs. 3 EStG) and must
        # never be floored at zero on its way out through the API.
        read = _to_read(
            _make_statement(
                gross_rental_income_cents=500_000,
                deductible_expenses_cents=300_000,
                building_acquisition_cost_cents=20_000_000,
                building_completion_year=2010,
            )
        )

        assert read.afa_deduction_cents == 400_000
        assert read.net_rental_income_cents == -200_000

    def test_higher_rate_band_for_a_building_completed_from_2023(self):
        read = _to_read(
            _make_statement(
                building_acquisition_cost_cents=20_000_000,
                building_completion_year=2024,  # 3% linear
            )
        )

        assert read.afa_deduction_cents == 600_000
