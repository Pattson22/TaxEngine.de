"""Unit tests for app/eric/cover_sheet.py -- the KOMPRIMIERT cover sheet
PDF. Pure/local, same pattern as tests/test_eric.py's TestXmlBuilder."""

import uuid

from app.eric.cover_sheet import _format_euros, build_cover_sheet_pdf
from app.models.enums import ChurchTaxType, FederalState, FilingStatus, SubmissionMode, TaxClass
from app.models.tax_filing import TaxFiling
from app.models.user import User


def _make_user(**overrides) -> User:
    defaults = dict(
        id=uuid.uuid4(),
        email="test@example.com",
        first_name="Anna",
        last_name="Muster",
        tax_identification_number="12345678901",
        steuernummer="27/815/08150",
        street="Musterstraße",
        house_number="1",
        postal_code="10115",
        city="Berlin",
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
        status=FilingStatus.ACCEPTED,
        submission_mode=SubmissionMode.KOMPRIMIERT,
        taxable_income_cents=43_680_00,
        income_tax_cents=8_708_00,
        solidarity_surcharge_cents=0,
        church_tax_cents=0,
        estimated_refund_cents=-2_495_00,
        elster_transfer_ticket="STUB-abc123",
    )
    defaults.update(overrides)
    return TaxFiling(**defaults)


class TestFormatEuros:
    def test_positive_cents_uses_german_grouping(self):
        assert _format_euros(1_234_56) == "1.234,56 €"

    def test_negative_cents_keeps_correct_magnitude(self):
        assert _format_euros(-2_495_00) == "-2.495,00 €"

    def test_none_defaults_to_zero(self):
        assert _format_euros(None) == "0,00 €"

    def test_small_amount_has_no_thousands_separator(self):
        assert _format_euros(50_00) == "50,00 €"


class TestBuildCoverSheetPdf:
    def test_returns_a_well_formed_pdf(self):
        pdf_bytes = build_cover_sheet_pdf(_make_user(), _make_filing())

        assert pdf_bytes.startswith(b"%PDF-")
        assert b"%%EOF" in pdf_bytes

    def test_includes_taxpayer_identity_and_transfer_ticket(self):
        pdf_bytes = build_cover_sheet_pdf(_make_user(), _make_filing())

        assert b"Muster" in pdf_bytes
        assert b"12345678901" in pdf_bytes  # Steuer-ID
        assert b"27/815/08150" in pdf_bytes  # Steuernummer
        assert b"STUB-abc123" in pdf_bytes  # Transferticket

    def test_handles_missing_optional_fields_gracefully(self):
        user = _make_user(street=None, house_number=None, postal_code=None, city=None, steuernummer=None)
        pdf_bytes = build_cover_sheet_pdf(user, _make_filing())

        assert pdf_bytes.startswith(b"%PDF-")
