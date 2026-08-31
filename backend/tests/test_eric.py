"""
Unit tests for the ERiC scaffold (app/eric/). xml_builder and
StubEricClient are pure/local -- no network, no DB needed to test them for
real. submission_service is tested with a mocked DB session (same pattern
as tests/test_payment_service.py) since it doesn't need a real database to
prove its own orchestration logic.
"""

import os
import uuid
from unittest.mock import MagicMock

import pytest

from app.eric import native_bindings
from app.eric.client import (
    EricSubmissionError,
    EricSubmissionResult,
    EricValidationError,
    NativeEricClient,
    StubEricClient,
)
from app.eric.submission_service import SubmissionError, submit_filing
from app.eric.xml_builder import _cents_to_euro_str, build_est_xml
from app.models.capital_income_statement import CapitalIncomeStatement
from app.models.enums import ChurchTaxType, FederalState, FilingStatus, TaxClass
from app.models.rental_property_statement import RentalPropertyStatement
from app.models.self_employment_statement import SelfEmploymentStatement
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

    def test_includes_capital_income_statements_and_their_tax(self):
        filing = _make_filing(
            capital_gains_tax_cents=25_000,
            capital_gains_soli_cents=1_375,
            capital_gains_church_tax_cents=0,
        )
        stmt = CapitalIncomeStatement(
            institution_name="Trade Republic",
            gross_income_cents=150_000,
            kapitalertragsteuer_withheld_cents=0,
        )

        xml = build_est_xml(_make_user(), filing, [], capital_income_statements=[stmt])

        assert "Trade Republic" in xml
        assert "1500.00" in xml  # gross capital income
        assert "250.00" in xml  # capital_gains_tax_cents -> euro
        assert "13.75" in xml  # capital_gains_soli_cents -> euro

    def test_includes_rental_property_statement_with_a_negative_net_result(self):
        # A loss-making property is a legitimate signed negative result
        # (§2 Abs. 3 EStG) -- must not come out mangled by divmod on a
        # negative cents value.
        filing = _make_filing(net_rental_income_cents=-55_000)
        stmt = RentalPropertyStatement(
            property_address="Musterstraße 1, Berlin",
            gross_rental_income_cents=100_000,
            deductible_expenses_cents=155_000,
        )

        xml = build_est_xml(_make_user(), filing, [], rental_property_statements=[stmt])

        assert "Musterstraße 1, Berlin" in xml
        assert "-550.00" in xml  # net rental loss, correctly signed

    def test_includes_self_employment_statement(self):
        filing = _make_filing(net_self_employment_income_cents=200_000)
        stmt = SelfEmploymentStatement(
            business_name="Muster Freelancing",
            gross_revenue_cents=500_000,
            deductible_expenses_cents=300_000,
        )

        xml = build_est_xml(_make_user(), filing, [], self_employment_statements=[stmt])

        assert "Muster Freelancing" in xml
        assert "2000.00" in xml  # net self-employment income

    def test_includes_kinderfreibetrag_when_applied(self):
        filing = _make_filing(
            number_of_children=2,
            kinderfreibetrag_applied=True,
            kinderfreibetrag_total_cents=1_234_00,
        )

        xml = build_est_xml(_make_user(), filing, [])

        assert "<AnzahlKinder>2</AnzahlKinder>" in xml
        assert "1234.00" in xml

    def test_includes_kindergeld_when_kinderfreibetrag_not_applied(self):
        filing = _make_filing(
            number_of_children=1,
            kinderfreibetrag_applied=False,
            kindergeld_received_cents=2_50000,
        )

        xml = build_est_xml(_make_user(), filing, [])

        assert "<KindergeldErhalten>2500.00</KindergeldErhalten>" in xml

    def test_omits_kinderfreibetrag_block_when_no_children(self):
        xml = build_est_xml(_make_user(), _make_filing(), [])
        assert "Kinderfreibetrag" not in xml


class TestCentsToEuroStr:
    def test_positive_cents(self):
        assert _cents_to_euro_str(150_000) == "1500.00"

    def test_negative_cents_keeps_correct_magnitude(self):
        assert _cents_to_euro_str(-55_000) == "-550.00"

    def test_none_defaults_to_zero(self):
        assert _cents_to_euro_str(None) == "0.00"


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


class _FakeFFI:
    """Stands in for cffi.FFI in tests -- real cffi cdata can't be built
    without a loaded library, so buffer handles here are plain Python
    objects rather than actual C pointers."""

    NULL = object()

    @staticmethod
    def buffer(content, length):
        return content[:length]


class _FakeHandle:
    def __init__(self):
        self.content = b""


class _FakeLib:
    """Fakes the subset of ericapi's C surface NativeEricClient calls,
    with return codes/buffer contents configurable per test -- mirrors
    real ERiC semantics closely enough to exercise client.py's branching
    without needing the actual proprietary library."""

    def __init__(
        self,
        *,
        init_ret=native_bindings.ERIC_OK,
        check_ret=native_bindings.ERIC_OK,
        check_text=b"",
        submit_ret=native_bindings.ERIC_OK,
        submit_rueckgabe=b"",
        error_text=b"",
    ):
        self.init_ret = init_ret
        self.check_ret = check_ret
        self.check_text = check_text
        self.submit_ret = submit_ret
        self.submit_rueckgabe = submit_rueckgabe
        self.error_text = error_text
        self.calls: list[tuple] = []

    def EricInitialisiere(self, plugin_path, log_path):
        self.calls.append(("init", plugin_path, log_path))
        return self.init_ret

    def EricBeende(self):
        self.calls.append(("beende",))
        return native_bindings.ERIC_OK

    def EricRueckgabepufferErzeugen(self):
        return _FakeHandle()

    def EricRueckgabepufferFreigeben(self, handle):
        self.calls.append(("freigeben", handle))
        return native_bindings.ERIC_OK

    def EricRueckgabepufferInhalt(self, handle):
        return handle.content

    def EricRueckgabepufferLaenge(self, handle):
        return len(handle.content)

    def EricCheckXML(self, xml, datenart_version, handle):
        self.calls.append(("check", xml, datenart_version))
        handle.content = self.check_text
        return self.check_ret

    def EricBearbeiteVorgang(
        self, xml, datenart_version, flags, druck_parameter, crypto_parameter, rueckgabe, serverantwort
    ):
        self.calls.append(("submit", xml, datenart_version, flags, druck_parameter, crypto_parameter))
        rueckgabe.content = self.submit_rueckgabe
        return self.submit_ret

    def EricHoleFehlerText(self, code, handle):
        handle.content = self.error_text or f"ERiC error {code}".encode()
        return native_bindings.ERIC_OK


def _make_native_client(monkeypatch, fake_lib: _FakeLib, plugin_path: str = "C:/fake/plugins") -> NativeEricClient:
    from app.eric import client as client_module

    fake_library = native_bindings.EricLibrary(ffi=_FakeFFI(), lib=fake_lib, plugin_path=plugin_path)
    monkeypatch.setattr(client_module.native_bindings, "load", lambda sdk_path: fake_library)
    return NativeEricClient(sdk_path="unused")


class TestNativeBindingsLoad:
    def test_raises_when_library_missing(self, tmp_path):
        with pytest.raises(native_bindings.EricLibraryNotFoundError):
            native_bindings.load(tmp_path)


class TestNativeEricClient:
    def test_validate_xml_requires_datenart_version(self, monkeypatch):
        client = _make_native_client(monkeypatch, _FakeLib())
        with pytest.raises(ValueError, match="datenart_version"):
            client.validate_xml("<Elster></Elster>")

    def test_validate_xml_passes_on_eric_ok(self, monkeypatch):
        fake_lib = _FakeLib(check_ret=native_bindings.ERIC_OK)
        client = _make_native_client(monkeypatch, fake_lib)

        client.validate_xml("<Elster></Elster>", datenart_version="ESt_2024")  # must not raise

        check_calls = [c for c in fake_lib.calls if c[0] == "check"]
        assert check_calls == [("check", b"<Elster></Elster>", b"ESt_2024")]

    def test_validate_xml_raises_with_eric_buffer_text_on_failure(self, monkeypatch):
        fake_lib = _FakeLib(
            check_ret=native_bindings.ERIC_GLOBAL_PRUEF_FEHLER,
            check_text="Feld E0100001 fehlt".encode("utf-8"),
        )
        client = _make_native_client(monkeypatch, fake_lib)

        with pytest.raises(EricValidationError, match="E0100001"):
            client.validate_xml("<Elster></Elster>", datenart_version="ESt_2024")

    def test_ericinitialisiere_runs_once_lazily_across_calls(self, monkeypatch):
        fake_lib = _FakeLib()
        client = _make_native_client(monkeypatch, fake_lib, plugin_path="C:/sdk/plugins")

        client.validate_xml("<Elster></Elster>", datenart_version="ESt_2024")
        client.validate_xml("<Elster></Elster>", datenart_version="ESt_2024")

        init_calls = [c for c in fake_lib.calls if c[0] == "init"]
        assert init_calls == [("init", b"C:/sdk/plugins", _FakeFFI.NULL)]

    def test_ericinitialisiere_failure_raises_submission_error(self, monkeypatch):
        fake_lib = _FakeLib(init_ret=610001001)
        client = _make_native_client(monkeypatch, fake_lib)

        with pytest.raises(EricSubmissionError, match="610001001"):
            client.validate_xml("<Elster></Elster>", datenart_version="ESt_2024")

    def test_submit_requires_datenart_version(self, monkeypatch):
        client = _make_native_client(monkeypatch, _FakeLib())
        with pytest.raises(ValueError, match="datenart_version"):
            client.submit("<Elster></Elster>")

    def test_submit_success_extracts_telenummer_and_sends_unauthenticated(self, monkeypatch):
        fake_lib = _FakeLib(
            submit_ret=native_bindings.ERIC_OK,
            submit_rueckgabe=(
                b'<EricBearbeiteVorgang xmlns="http://www.elster.de/EricXML/1.1/EricBearbeiteVorgang">'
                b"<Erfolg><Telenummer>N55</Telenummer></Erfolg></EricBearbeiteVorgang>"
            ),
        )
        client = _make_native_client(monkeypatch, fake_lib)

        result = client.submit("<Elster></Elster>", datenart_version="ESt_2024")

        assert result.accepted is True
        assert result.transfer_ticket == "N55"

        (_, xml, datenart_version, flags, druck_parameter, crypto_parameter) = next(
            c for c in fake_lib.calls if c[0] == "submit"
        )
        assert xml == b"<Elster></Elster>"
        assert datenart_version == b"ESt_2024"
        assert flags == native_bindings.ERIC_VALIDIERE | native_bindings.ERIC_SENDE
        # KOMPRIMIERT/unauthenticated: no print request, no crypto/cert parameter.
        assert druck_parameter is _FakeFFI.NULL
        assert crypto_parameter is _FakeFFI.NULL

    def test_submit_pruef_fehler_raises_validation_error(self, monkeypatch):
        fake_lib = _FakeLib(
            submit_ret=native_bindings.ERIC_GLOBAL_PRUEF_FEHLER,
            submit_rueckgabe=b"<EricBearbeiteVorgang><FehlerRegelpruefung /></EricBearbeiteVorgang>",
        )
        client = _make_native_client(monkeypatch, fake_lib)

        with pytest.raises(EricValidationError, match="FehlerRegelpruefung"):
            client.submit("<Elster></Elster>", datenart_version="ESt_2024")

    def test_submit_other_failure_raises_submission_error_with_error_text(self, monkeypatch):
        fake_lib = _FakeLib(submit_ret=999, error_text=b"transport failure")
        client = _make_native_client(monkeypatch, fake_lib)

        with pytest.raises(EricSubmissionError, match="transport failure"):
            client.submit("<Elster></Elster>", datenart_version="ESt_2024")

    def test_close_calls_eric_beende_only_if_initialized(self, monkeypatch):
        fake_lib = _FakeLib()
        client = _make_native_client(monkeypatch, fake_lib)

        client.close()  # never initialized -- must not call EricBeende
        assert ("beende",) not in fake_lib.calls

        client.validate_xml("<Elster></Elster>", datenart_version="ESt_2024")
        client.close()
        assert ("beende",) in fake_lib.calls
        assert client._initialized is False


_REAL_SDK_PATH = os.environ.get("ERIC_SDK_PATH")


@pytest.mark.skipif(
    not _REAL_SDK_PATH,
    reason="ERIC_SDK_PATH not set -- point it at an extracted ERiC SDK platform "
    "directory to run this against the real proprietary library.",
)
class TestNativeEricClientAgainstRealLibrary:
    """Opt-in integration test: proves native_bindings.py's cdef actually
    matches the real ericapi.dll/.so ABI, not just a plausible-looking
    guess. Verified manually against ERiC 44.2.4.1/Windows-x86_64: garbage
    XML is rejected with a real German plausibility error, and the SDK's
    own est_e10_2024.xml example passes EricCheckXML cleanly."""

    def test_initialises_and_validates_against_real_library(self):
        client = NativeEricClient(sdk_path=_REAL_SDK_PATH)
        try:
            with pytest.raises(EricValidationError):
                client.validate_xml("<not>real</not>", datenart_version="ESt_2024")
        finally:
            client.close()


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
