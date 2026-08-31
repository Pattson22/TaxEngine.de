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

from app.api.routes.tax_filings import (
    calculate_filing,
    create_tax_filing,
    get_cover_sheet,
    get_submission_job,
    list_supported_tax_years,
    mark_cover_sheet_mailed,
    submit_tax_filing,
)
from app.models.enums import EricSubmissionJobStatus, FilingStatus, SubmissionMode
from app.models.eric_submission_job import EricSubmissionJob
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


def _accepted_komprimiert_filing(**overrides) -> tuple[TaxFiling, User]:
    user = User(id=uuid.uuid4(), first_name="Anna", last_name="Muster")
    defaults = dict(
        id=uuid.uuid4(),
        user_id=user.id,
        tax_year=2024,
        status=FilingStatus.ACCEPTED,
        submission_mode=SubmissionMode.KOMPRIMIERT,
        elster_transfer_ticket="STUB-abc123",
    )
    defaults.update(overrides)
    filing = TaxFiling(**defaults)
    return filing, user


class TestGetCoverSheet:
    def test_rejects_authentifiziert_filing(self):
        filing, user = _accepted_komprimiert_filing(submission_mode=SubmissionMode.AUTHENTIFIZIERT)
        db = MagicMock()
        db.get.return_value = filing

        with pytest.raises(HTTPException) as exc_info:
            get_cover_sheet(filing.id, current_user=user, db=db)

        assert exc_info.value.status_code == 409

    def test_rejects_filing_not_yet_submitted(self):
        filing, user = _accepted_komprimiert_filing(status=FilingStatus.FEE_PAID)
        db = MagicMock()
        db.get.return_value = filing

        with pytest.raises(HTTPException) as exc_info:
            get_cover_sheet(filing.id, current_user=user, db=db)

        assert exc_info.value.status_code == 409

    def test_successful_download_returns_pdf_and_records_generated_at(self):
        filing, user = _accepted_komprimiert_filing()
        db = MagicMock()
        db.get.return_value = filing
        assert filing.cover_sheet_generated_at is None

        response = get_cover_sheet(filing.id, current_user=user, db=db)

        assert response.media_type == "application/pdf"
        assert response.body.startswith(b"%PDF-")
        assert filing.cover_sheet_generated_at is not None
        db.commit.assert_called_once()

    def test_redownload_does_not_overwrite_generated_at(self):
        import datetime

        first_generated_at = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
        filing, user = _accepted_komprimiert_filing(cover_sheet_generated_at=first_generated_at)
        db = MagicMock()
        db.get.return_value = filing

        get_cover_sheet(filing.id, current_user=user, db=db)

        assert filing.cover_sheet_generated_at == first_generated_at
        db.commit.assert_not_called()


class TestMarkCoverSheetMailed:
    def test_rejects_when_cover_sheet_never_generated(self):
        filing, user = _accepted_komprimiert_filing()
        db = MagicMock()
        db.get.return_value = filing

        with pytest.raises(HTTPException) as exc_info:
            mark_cover_sheet_mailed(filing.id, current_user=user, db=db)

        assert exc_info.value.status_code == 409

    def test_records_mailed_timestamp(self):
        import datetime

        filing, user = _accepted_komprimiert_filing(
            cover_sheet_generated_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
        )
        db = MagicMock()
        db.get.return_value = filing

        result = mark_cover_sheet_mailed(filing.id, current_user=user, db=db)

        assert result.cover_sheet_mailed_at is not None
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(filing)


def _fee_paid_filing(**overrides) -> tuple[TaxFiling, User]:
    user = User(id=uuid.uuid4(), tax_identification_number="12345678901")
    defaults = dict(
        id=uuid.uuid4(),
        user_id=user.id,
        tax_year=2024,
        status=FilingStatus.FEE_PAID,
    )
    defaults.update(overrides)
    filing = TaxFiling(**defaults)
    return filing, user


class TestSubmitTaxFiling:
    """submit_tax_filing only enqueues a job now -- see
    app/eric/submission_service.py's module docstring for why the actual
    ERiC call moved to the eric-submitter worker, out of this web process."""

    def test_rejects_filing_not_fee_paid(self):
        filing, user = _fee_paid_filing(status=FilingStatus.CALCULATED)
        db = MagicMock()
        db.get.return_value = filing

        with pytest.raises(HTTPException) as exc_info:
            submit_tax_filing(filing.id, current_user=user, db=db)

        assert exc_info.value.status_code == 409
        assert "FEE_PAID" in exc_info.value.detail

    def test_rejects_missing_steuer_id(self):
        filing, user = _fee_paid_filing()
        user.tax_identification_number = None
        db = MagicMock()
        db.get.return_value = filing

        with pytest.raises(HTTPException) as exc_info:
            submit_tax_filing(filing.id, current_user=user, db=db)

        assert exc_info.value.status_code == 409
        assert "Steuer-ID" in exc_info.value.detail

    def test_enqueues_a_job_for_a_valid_filing(self):
        filing, user = _fee_paid_filing()
        db = MagicMock()
        db.get.return_value = filing

        with patch("app.api.routes.tax_filings.enqueue_submission") as mocked_enqueue:
            mocked_enqueue.return_value = EricSubmissionJob(
                tax_filing_id=filing.id, status=EricSubmissionJobStatus.PENDING
            )
            result = submit_tax_filing(filing.id, current_user=user, db=db)

        mocked_enqueue.assert_called_once_with(db, filing)
        assert result.status == EricSubmissionJobStatus.PENDING
        assert result.tax_filing_id == filing.id


class TestGetSubmissionJob:
    def test_404_when_nothing_queued_yet(self):
        filing, user = _fee_paid_filing()
        db = MagicMock()
        db.get.return_value = filing
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            get_submission_job(filing.id, current_user=user, db=db)

        assert exc_info.value.status_code == 404

    def test_returns_the_most_recent_job(self):
        filing, user = _fee_paid_filing()
        job = EricSubmissionJob(
            tax_filing_id=filing.id, status=EricSubmissionJobStatus.SUCCEEDED, transfer_ticket="TICKET-1"
        )
        db = MagicMock()
        db.get.return_value = filing
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = job

        result = get_submission_job(filing.id, current_user=user, db=db)

        assert result is job
