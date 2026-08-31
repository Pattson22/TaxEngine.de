"""
Unit tests for app/eric_submitter/worker.py's job-processing logic.
Mocks the DB session and NativeEricClient the same way tests/test_eric.py
mocks EricClient for submit_filing -- no real database or ERiC library
needed to prove the claim/process/persist logic itself is correct.
"""

import uuid
from datetime import date
from unittest.mock import MagicMock

import pytest

from app.eric.client import EricSubmissionResult, EricValidationError
from app.eric_submitter.worker import _claim_next_job, _process_job
from app.models.enums import ChurchTaxType, EricSubmissionJobStatus, FederalState, FilingStatus, TaxClass
from app.models.eric_submission_job import EricSubmissionJob
from app.models.tax_filing import TaxFiling
from app.models.user import User


def _make_user(**overrides) -> User:
    defaults = dict(
        id=uuid.uuid4(),
        email="test@example.com",
        first_name="Anna",
        last_name="Muster",
        tax_identification_number="12345678901",
        date_of_birth=date(1988, 7, 9),
        residence_state=FederalState.BAYERN,
        tax_class=TaxClass.I,
        church_tax_type=ChurchTaxType.NONE,
        is_joint_assessment=False,
        steuernummer="191/815/08155",
        finanzamt_bufa_nummer="9181",
    )
    defaults.update(overrides)
    return User(**defaults)


def _make_filing(**overrides) -> TaxFiling:
    defaults = dict(id=uuid.uuid4(), tax_year=2024, status=FilingStatus.FEE_PAID)
    defaults.update(overrides)
    return TaxFiling(**defaults)


def _make_job(filing_id, **overrides) -> EricSubmissionJob:
    defaults = dict(id=uuid.uuid4(), tax_filing_id=filing_id, status=EricSubmissionJobStatus.PROCESSING)
    defaults.update(overrides)
    return EricSubmissionJob(**defaults)


class TestClaimNextJob:
    def test_returns_none_when_queue_empty(self):
        db = MagicMock()
        db.execute.return_value.scalars.return_value.first.return_value = None

        assert _claim_next_job(db) is None
        db.commit.assert_not_called()

    def test_marks_claimed_job_processing(self):
        db = MagicMock()
        job = _make_job(uuid.uuid4(), status=EricSubmissionJobStatus.PENDING)
        db.execute.return_value.scalars.return_value.first.return_value = job

        claimed = _claim_next_job(db)

        assert claimed is job
        assert job.status == EricSubmissionJobStatus.PROCESSING
        assert job.claimed_at is not None
        db.commit.assert_called_once()


class TestProcessJob:
    def _db_for(self, filing, user):
        db = MagicMock()
        db.get.side_effect = lambda model, id_: filing if model is TaxFiling else user
        db.query.return_value.filter.return_value.all.return_value = []  # no wage certs etc.
        return db

    def test_missing_filing_fails_job(self):
        db = MagicMock()
        db.get.return_value = None
        job = _make_job(uuid.uuid4())

        _process_job(db, MagicMock(), job)

        assert job.status == EricSubmissionJobStatus.FAILED
        assert "no longer exists" in job.error_message

    def test_already_transferred_filing_short_circuits_as_success(self):
        filing = _make_filing(status=FilingStatus.ACCEPTED)
        filing.elster_transfer_ticket = "EXISTING-TICKET"
        user = _make_user()
        db = self._db_for(filing, user)
        job = _make_job(filing.id)

        _process_job(db, MagicMock(), job)

        assert job.status == EricSubmissionJobStatus.SUCCEEDED
        assert job.transfer_ticket == "EXISTING-TICKET"

    def test_filing_not_fee_paid_fails_job(self):
        filing = _make_filing(status=FilingStatus.DRAFT)
        user = _make_user()
        db = self._db_for(filing, user)
        job = _make_job(filing.id)

        _process_job(db, MagicMock(), job)

        assert job.status == EricSubmissionJobStatus.FAILED
        assert "FEE_PAID" in job.error_message

    def test_user_without_steuer_id_fails_job(self):
        filing = _make_filing()
        user = _make_user(tax_identification_number=None)
        db = self._db_for(filing, user)
        job = _make_job(filing.id)

        _process_job(db, MagicMock(), job)

        assert job.status == EricSubmissionJobStatus.FAILED
        assert "Steuer-ID" in job.error_message

    def test_successful_submission_marks_filing_accepted_and_job_succeeded(self):
        filing = _make_filing()
        user = _make_user()
        db = self._db_for(filing, user)
        job = _make_job(filing.id)

        eric_client = MagicMock()
        eric_client.format_steuernummer_for_elster.return_value = "9181081508155"
        eric_client.validate_xml.return_value = None
        eric_client.submit.return_value = EricSubmissionResult(transfer_ticket="TICKET-1", accepted=True)

        _process_job(db, eric_client, job)

        eric_client.format_steuernummer_for_elster.assert_called_once_with(
            "191/815/08155", bundesfinanzamtsnr="9181"
        )
        assert filing.status == FilingStatus.ACCEPTED
        assert filing.elster_transfer_ticket == "TICKET-1"
        assert job.status == EricSubmissionJobStatus.SUCCEEDED
        assert job.transfer_ticket == "TICKET-1"

    def test_stnr_conversion_failure_is_non_fatal(self):
        filing = _make_filing()
        user = _make_user()
        db = self._db_for(filing, user)
        job = _make_job(filing.id)

        eric_client = MagicMock()
        eric_client.format_steuernummer_for_elster.side_effect = EricValidationError("bad Steuernummer")
        eric_client.validate_xml.return_value = None
        eric_client.submit.return_value = EricSubmissionResult(transfer_ticket="TICKET-2", accepted=True)

        _process_job(db, eric_client, job)

        # Submission still proceeds (Vorsatz just gets omitted) rather
        # than failing the whole job over a non-essential block.
        assert job.status == EricSubmissionJobStatus.SUCCEEDED
        assert filing.status == FilingStatus.ACCEPTED

    def test_eric_rejection_fails_job_and_records_reason_on_filing(self):
        filing = _make_filing()
        user = _make_user()
        db = self._db_for(filing, user)
        job = _make_job(filing.id)

        eric_client = MagicMock()
        eric_client.format_steuernummer_for_elster.return_value = "9181081508155"
        eric_client.validate_xml.side_effect = EricValidationError("Feld E0100001 fehlt")

        _process_job(db, eric_client, job)

        assert job.status == EricSubmissionJobStatus.FAILED
        assert "E0100001" in job.error_message
        assert "E0100001" in filing.elster_rejection_reason
