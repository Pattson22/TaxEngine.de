"""
Regression test for the /tax-filings/{id}/calculate route's error handling.

TaxFilingCreate.tax_year only validates 2015 <= year <= 2100, so a filing
row can exist for a tax_year outside SUPPORTED_TAX_YEARS (constants.py).
Calculating such a filing makes tax_engine.constants.get_constants_for_year
raise a plain ValueError. The route used to catch only TaxCalculationError
(a ValueError subclass), so that plain ValueError fell through as an
unhandled 500 instead of the intended 422. Covered here directly against
the route function (mocked db/user), matching this test suite's DB-free
convention -- no TestClient/live Postgres fixture exists in this repo.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.routes.tax_filings import calculate_filing
from app.models.enums import FilingStatus
from app.models.tax_filing import TaxFiling
from app.models.user import User


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
