"""
Tests for the /tax-filings routes' handling of tax years outside
SUPPORTED_TAX_YEARS (tax_engine/constants.py), covered directly against
the route functions (mocked db/user) -- matching this test suite's
DB-free convention, since no TestClient/live Postgres fixture exists in
this repo.

- calculate_filing: a filing can exist for an unsupported year (see
  below), and calculating it makes get_constants_for_year raise a plain
  ValueError. The route used to catch only TaxCalculationError (a
  ValueError subclass), so that plain ValueError fell through as an
  unhandled 500 instead of the intended 422.
- create_tax_filing: TaxFilingCreate.tax_year only validates
  2015 <= year <= 2100, so without an explicit check a filing could be
  created for a year the engine can't calculate at all -- the year
  picker (frontend) sources its options from list_supported_tax_years,
  but the API must not trust the client to only ever send those options.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.routes.tax_filings import calculate_filing, create_tax_filing, list_supported_tax_years
from app.models.enums import FilingStatus
from app.models.tax_filing import TaxFiling
from app.models.user import User
from app.schemas.tax_filing import TaxFilingCreate


def _owned_filing(tax_year: int) -> tuple[TaxFiling, User]:
    user = User(id=uuid.uuid4())
    filing = TaxFiling(id=uuid.uuid4(), user_id=user.id, tax_year=tax_year, status=FilingStatus.DRAFT)
    return filing, user


class TestCalculateFilingUnsupportedYear:
    def test_plain_value_error_becomes_422_not_500(self):
        filing, user = _owned_filing(2023)
        db = MagicMock()
        db.get.return_value = filing

        with patch(
            "app.api.routes.tax_filings.calculate_tax_filing",
            side_effect=ValueError(
                "No verified tax constants available for tax_year=2023. Supported years: [2024]."
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                calculate_filing(filing.id, current_user=user, db=db)

        assert exc_info.value.status_code == 422
        assert "2023" in exc_info.value.detail
        db.rollback.assert_called_once()

    def test_supported_year_is_unaffected(self):
        filing, user = _owned_filing(2024)
        db = MagicMock()
        db.get.return_value = filing

        with patch(
            "app.api.routes.tax_filings.calculate_tax_filing", return_value=filing
        ) as mocked_calculate:
            result = calculate_filing(filing.id, current_user=user, db=db)

        mocked_calculate.assert_called_once_with(db, user, 2024)
        assert result is filing
        db.commit.assert_called_once()


class TestCreateTaxFilingUnsupportedYear:
    def test_unsupported_year_is_rejected_before_touching_the_db(self):
        user = User(id=uuid.uuid4())
        db = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            create_tax_filing(TaxFilingCreate(tax_year=2023), current_user=user, db=db)

        assert exc_info.value.status_code == 422
        assert "2023" in exc_info.value.detail
        db.add.assert_not_called()
        db.commit.assert_not_called()

    def test_supported_year_is_created(self):
        user = User(id=uuid.uuid4())
        db = MagicMock()
        db.query.return_value.filter.return_value.one_or_none.return_value = None

        filing = create_tax_filing(TaxFilingCreate(tax_year=2024), current_user=user, db=db)

        assert filing.tax_year == 2024
        assert filing.user_id == user.id
        db.add.assert_called_once()
        db.commit.assert_called_once()


class TestListSupportedTaxYears:
    def test_returns_the_currently_reviewed_years(self):
        assert list_supported_tax_years() == [2024]
