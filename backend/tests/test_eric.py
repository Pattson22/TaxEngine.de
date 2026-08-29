"""
Unit tests for the ERiC scaffold (app/eric/). xml_builder and
StubEricClient are pure/local -- no network, no DB needed to test them for
real. submission_service is tested with a mocked DB session (same pattern
as tests/test_payment_service.py) since it doesn't need a real database to
prove its own orchestration logic.
"""

import uuid
from unittest.mock import MagicMock

import pytest

from app.eric.client import (
    EricSubmissionResult,
    EricValidationError,
    NativeEricClient,
    StubEricClient,
)
from app.eric.submission_service import SubmissionError, submit_filing
from app.eric.xml_builder import build_est_xml
from app.models.enums import ChurchTaxType, FederalState, FilingStatus, TaxClass
from app.models.tax_filing import TaxFiling
from app.models.user import User
from app.models.wage_tax_certificate import WageTaxCertificate


def _make_user(**overrides) -> User:
    defaults = dict(
        id=uuid.uuid4(),
        email="test@example.com",
        first_name="Anna",
        last_name="Muster",
        tax_identification_number="12345678901",
        residence_state=FederalState.BERLIN,
        tax_class=TaxClass.I,
        church_tax_type=ChurchTaxType.NONE,
    )
    defaults.update(overrides)
    return User(**defaults)


def _make_filing(**overrides) -> TaxFiling:
    defaults = dict(
        id=uuid.uuid4(),
        tax_year=2024,
        status=FilingStatus.FEE_PAID,
        taxable_income_cents=43_680_00,
        income_tax_cents=8_708_00,
        solidarity_surcharge_cents=0,
        church_tax_cents=0,
    )
    defaults.update(overrides)
    return TaxFiling(**defaults)


class TestXmlBuilder:
    def test_produces_well_formed_xml_with_expected_fields(self):
        user = _make_user()
        filing = _make_filing()
        wtc = WageTaxCertificate(
            employer_name="Muster GmbH", gross_wage_cents=45_000_00, income_tax_withheld_cents=2_500_00
        )

        xml = build_est_xml(user, filing, [wtc])

        assert "<Elster" in xml
        assert "12345678901" in xml  # Steuer-ID
        assert "Muster" in xml
        assert "45000.00" in xml  # gross wage, cents -> euro string
        assert "8708.00" in xml  # income tax

    def test_handles_no_wage_certificates(self):
        xml = build_est_xml(_make_user(), _make_filing(), [])
        assert "<Elster" in xml

    def test_handles_missing_steuer_id_gracefully(self):
        user = _make_user(tax_identification_number=None)
        xml = build_est_xml(user, _make_filing(), [])
        assert "<SteuerId />" in xml or "<SteuerId></SteuerId>" in xml


class TestStubEricClient:
    def test_validates_well_formed_elster_xml(self):
        client = StubEricClient()
        xml = build_est_xml(_make_user(), _make_filing(), [])
        client.validate_xml(xml)  # must not raise

    def test_rejects_malformed_xml(self):
        client = StubEricClient()
        with pytest.raises(EricValidationError):
            client.validate_xml("<not><closed>")

    def test_rejects_wrong_root_element(self):
        client = StubEricClient()
        with pytest.raises(EricValidationError):
            client.validate_xml("<SomethingElse></SomethingElse>")

    def test_submit_returns_accepted_with_stub_prefixed_ticket(self):
        client = StubEricClient()
        xml = build_est_xml(_make_user(), _make_filing(), [])

        result = client.submit(xml)

        assert result.accepted is True
        assert result.transfer_ticket.startswith("STUB-")


class TestNativeEricClientIsUnimplemented:
    def test_validate_xml_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            NativeEricClient().validate_xml("<Elster></Elster>")

    def test_submit_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            NativeEricClient().submit("<Elster></Elster>")


class TestSubmitFiling:
    def test_rejects_filing_not_fee_paid(self):
        db = MagicMock()
        user = _make_user()
        filing = _make_filing(status=FilingStatus.DRAFT)

        with pytest.raises(SubmissionError, match="FEE_PAID"):
            submit_filing(db, user, filing)

    def test_rejects_user_without_steuer_id(self):
        db = MagicMock()
        user = _make_user(tax_identification_number=None)
        filing = _make_filing()

        with pytest.raises(SubmissionError, match="Steuer-ID"):
            submit_filing(db, user, filing)

    def test_successful_submission_marks_filing_accepted(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []  # no wage certs
        user = _make_user()
        filing = _make_filing()

        result = submit_filing(db, user, filing, eric_client=StubEricClient())

        assert result.status == FilingStatus.ACCEPTED
        assert result.elster_transfer_ticket.startswith("STUB-")
        assert result.elster_submitted_at is not None
        assert result.elster_accepted_at is not None
        db.commit.assert_called_once()

    def test_eric_validation_failure_records_rejection_reason(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        user = _make_user()
        filing = _make_filing()

        failing_client = MagicMock()
        failing_client.validate_xml.side_effect = EricValidationError("bad field X")

        with pytest.raises(SubmissionError):
            submit_filing(db, user, filing, eric_client=failing_client)

        assert filing.elster_rejection_reason is not None
        assert "bad field X" in filing.elster_rejection_reason
        db.commit.assert_called_once()

    def test_eric_submit_returning_not_accepted_marks_filing_rejected(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        user = _make_user()
        filing = _make_filing()

        rejecting_client = MagicMock()
        rejecting_client.validate_xml.return_value = None
        rejecting_client.submit.return_value = EricSubmissionResult(
            transfer_ticket="TICKET-1", accepted=False, rejection_reason="Finanzamt says no"
        )

        result = submit_filing(db, user, filing, eric_client=rejecting_client)

        assert result.status == FilingStatus.REJECTED
        assert result.elster_rejection_reason == "Finanzamt says no"
        assert result.elster_transfer_ticket == "TICKET-1"
