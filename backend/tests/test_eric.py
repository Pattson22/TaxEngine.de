"""
Unit tests for the ERiC scaffold (app/eric/). xml_builder and
StubEricClient are pure/local -- no network, no DB needed to test them for
real. submission_service is tested with a mocked DB session (same pattern
as tests/test_payment_service.py) since it doesn't need a real database to
prove its own orchestration logic.
"""

import os
import uuid
import xml.etree.ElementTree as ET
from datetime import date
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
from app.eric.xml_builder import _cents_to_euro_str, _cents_to_whole_euro_str, build_est_xml
from app.models.capital_income_statement import CapitalIncomeStatement
from app.models.child import Child
from app.models.deduction import Deduction
from app.models.enums import (
    ChildRelationshipType,
    ChurchTaxType,
    DeductionCategory,
    FederalState,
    FilingStatus,
    TaxClass,
)
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
        date_of_birth=date(1988, 7, 9),
        street="Hermann-Geib-Str.",
        house_number="3",
        postal_code="93047",
        city="Regensburg",
        residence_state=FederalState.BERLIN,
        tax_class=TaxClass.I,
        church_tax_type=ChurchTaxType.NONE,
        is_joint_assessment=False,
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
    """Every field code asserted here is a real E10 identifier, verified
    against the ERiC 44.2.4.1 SDK's own E10-2024.xsd schema annotations
    and est_e10_2024.xml example (see xml_builder.py's module docstring) --
    not the old illustrative element names."""

    def test_produces_well_formed_real_envelope(self):
        user = _make_user()
        filing = _make_filing()

        xml = build_est_xml(user, filing, [], hersteller_id="12345")

        root = ET.fromstring(xml)
        assert root.tag.endswith("Elster")
        assert xml.count("http://www.elster.de/elsterxml/schema/v11") >= 1
        assert "<HerstellerID>12345</HerstellerID>" in xml
        assert "<Vorgang>send-NoSig</Vorgang>" in xml  # unauthenticated/KOMPRIMIERT
        assert 'xmlns="http://finkonsens.de/elster/elstererklaerung/est/e10/v2024"' in xml
        assert '<E10 xmlns=' in xml and 'version="2024"' in xml

    def test_hersteller_id_is_required(self):
        with pytest.raises(TypeError):
            build_est_xml(_make_user(), _make_filing(), [])  # type: ignore[call-arg]

    def test_maps_primary_filer_personal_data(self):
        user = _make_user(
            first_name="Horst",
            last_name="Mustermann",
            tax_identification_number="12345678901",
            date_of_birth=date(1982, 4, 9),
            street="Hermann-Geib-Str.",
            house_number="3",
            postal_code="93047",
            city="Regensburg",
            church_tax_type=ChurchTaxType.ROEMISCH_KATHOLISCH,
        )

        xml = build_est_xml(user, _make_filing(), [], hersteller_id="12345")

        assert "<E0100081>12345678901</E0100081>" in xml  # Identifikationsnummer
        assert "<E0100401>09.04.1982</E0100401>" in xml  # Geburtsdatum
        assert "<E0100201>Mustermann</E0100201>" in xml  # Name
        assert "<E0100301>Horst</E0100301>" in xml  # Vorname
        assert "<E0100402>03</E0100402>" in xml  # Religion -- Römisch-katholisch
        assert "<E0101104>Hermann-Geib-Str.</E0101104>" in xml  # Straße
        assert "<E0101206>3</E0101206>" in xml  # Hausnummer
        assert "<E0100601>93047</E0100601>" in xml  # PLZ
        assert "<E0100602>Regensburg</E0100602>" in xml  # Wohnort

    def test_omits_optional_personal_fields_that_have_no_value(self):
        user = _make_user(date_of_birth=None, street=None, house_number=None, postal_code=None, city=None)

        xml = build_est_xml(user, _make_filing(), [], hersteller_id="12345")

        for tag in ("E0100401", "E0101104", "E0101206", "E0100601", "E0100602"):
            assert f"<{tag}>" not in xml

    def test_church_tax_type_other_is_not_guessed_at(self):
        # OTHER covers many distinct real Religionsschluessel codes -- must
        # be omitted, never mapped to an arbitrary one of them.
        user = _make_user(church_tax_type=ChurchTaxType.OTHER)

        xml = build_est_xml(user, _make_filing(), [], hersteller_id="12345")

        assert "<E0100402>" not in xml

    def test_zusammenveranlagung_flag_and_spouse_block_when_joint(self):
        spouse = _make_user(
            first_name="Carolina",
            last_name="Mustermann",
            tax_identification_number="10987654321",
            date_of_birth=date(1988, 7, 9),
            church_tax_type=ChurchTaxType.EVANGELISCH,
        )
        user = _make_user(is_joint_assessment=True)
        user.spouse = spouse

        xml = build_est_xml(user, _make_filing(), [], hersteller_id="12345")

        assert "<Vlg_Art><E0101201>X</E0101201></Vlg_Art>" in xml  # Zusammenveranlagung
        assert "<E0100082>10987654321</E0100082>" in xml  # spouse Identifikationsnummer
        assert "<E0101001>09.07.1988</E0101001>" in xml  # spouse Geburtsdatum
        assert "<E0100901>Mustermann</E0100901>" in xml  # spouse Name
        assert "<E0100801>Carolina</E0100801>" in xml  # spouse Vorname
        assert "<E0101002>02</E0101002>" in xml  # spouse Religion -- Evangelisch

    def test_no_spouse_block_when_not_joint_assessment(self):
        xml = build_est_xml(_make_user(is_joint_assessment=False), _make_filing(), [], hersteller_id="12345")
        assert "Vlg_Art" not in xml
        assert "<B>" not in xml

    def test_no_n_block_when_no_wage_certificates(self):
        xml = build_est_xml(_make_user(), _make_filing(), [], hersteller_id="12345")
        assert "<N>" not in xml

    def test_single_wage_certificate_maps_to_lstb_einz_and_sum(self):
        user = _make_user(tax_class=TaxClass.III)
        cert = WageTaxCertificate(
            employer_name="Muster GmbH",
            gross_wage_cents=67_554_76,
            income_tax_withheld_cents=17_653_65,
            solidarity_surcharge_cents=3_543_54,
            church_tax_withheld_cents=775_43,
        )

        xml = build_est_xml(user, _make_filing(), [cert], hersteller_id="12345")

        assert "<Person>PersonA</Person>" in xml
        # Einz: 2-decimal figures for this one certificate -- COMMA decimal
        # separator, confirmed required by the real DezimalzahlXxx regex
        # facets (a period is a schema violation, not a style choice).
        assert "<E0200204>67554,76</E0200204>" in xml
        assert "<E0200304>17653,65</E0200304>" in xml
        assert "<E0200404>3543,54</E0200404>" in xml
        assert "<E0200504>775,43</E0200504>" in xml
        # Sum: Steuerklasse + whole-euro gross wage (E0200201), decimal for the rest.
        assert "<E0200002>3</E0200002>" in xml
        assert "<E0200201>67554</E0200201>" in xml
        assert "<E0200301>17653,65</E0200301>" in xml
        assert "<E0200401>3543,54</E0200401>" in xml
        assert "<E0200501>775,43</E0200501>" in xml

    def test_multiple_wage_certificates_sum_aggregates_across_employers(self):
        certs = [
            WageTaxCertificate(
                employer_name="Employer A",
                gross_wage_cents=30_000_00,
                income_tax_withheld_cents=5_000_00,
                solidarity_surcharge_cents=200_00,
                church_tax_withheld_cents=100_00,
            ),
            WageTaxCertificate(
                employer_name="Employer B",
                gross_wage_cents=15_000_50,
                income_tax_withheld_cents=2_000_00,
                solidarity_surcharge_cents=50_00,
                church_tax_withheld_cents=0,
            ),
        ]

        xml = build_est_xml(_make_user(), _make_filing(), certs, hersteller_id="12345")

        assert xml.count("<LStB_1_5_Einz>") == 2
        assert "<E0200201>45000</E0200201>" in xml  # 30000.00 + 15000.50, truncated to whole euros
        assert "<E0200301>7000,00</E0200301>" in xml
        assert "<E0200401>250,00</E0200401>" in xml
        assert "<E0200501>100,00</E0200501>" in xml

    def test_no_kap_v_s_kind_blocks_when_none_supplied(self):
        xml = build_est_xml(_make_user(), _make_filing(), [], hersteller_id="12345")
        assert "<KAP>" not in xml
        assert "<V>" not in xml
        assert "<S>" not in xml
        assert "<Kind>" not in xml

    def test_child_maps_identity_and_kindschaftsverhaeltnis(self):
        child = Child(
            first_name="Tobias",
            last_name=None,
            date_of_birth=date(2014, 8, 20),
            tax_identification_number="07792563183",
            relationship_type=ChildRelationshipType.BIOLOGICAL_OR_ADOPTED,
        )

        xml = build_est_xml(
            _make_user(is_joint_assessment=False), _make_filing(), [], children=[child], hersteller_id="12345"
        )

        assert "<E0500406>07792563183</E0500406>" in xml  # Identifikationsnummer
        assert "<E0500107>Tobias</E0500107>" in xml  # Vorname
        assert "E0500108" not in xml  # no abweichender Familienname supplied
        assert "<E0500701>20.08.2014</E0500701>" in xml  # Geburtsdatum
        assert "<E0500703>01.01-31.12</E0500703>" in xml  # full-year residency
        assert "<E0500807>1</E0500807>" in xml  # Kindschaftsverhältnis -- biological/adopted
        assert "<E0500601>01.01-31.12</E0500601>" in xml
        assert "K_Verh_B" not in xml  # not joint assessment -- only Person A's relationship

    def test_child_maps_abweichender_familienname_when_different(self):
        child = Child(
            first_name="Tobias", last_name="Anderername", date_of_birth=date(2014, 8, 20),
            relationship_type=ChildRelationshipType.FOSTER,
        )

        xml = build_est_xml(_make_user(), _make_filing(), [], children=[child], hersteller_id="12345")

        assert "<E0500108>Anderername</E0500108>" in xml
        assert "<E0500807>2</E0500807>" in xml  # Pflegekind

    def test_child_emits_k_verh_b_for_both_spouses_when_joint(self):
        spouse = _make_user(first_name="Carolina", last_name="Mustermann")
        user = _make_user(is_joint_assessment=True)
        user.spouse = spouse
        child = Child(
            first_name="Regina", date_of_birth=date(2018, 5, 6),
            relationship_type=ChildRelationshipType.GRANDCHILD_OR_STEP,
        )

        xml = build_est_xml(user, _make_filing(), [], children=[child], hersteller_id="12345")

        assert "<E0500807>3</E0500807>" in xml  # K_Verh_A -- Enkelkind/Stiefkind
        assert "<E0500808>3</E0500808>" in xml  # K_Verh_B -- same relationship, both spouses
        assert "<E0500805>01.01-31.12</E0500805>" in xml

    def test_up_to_14_children_mapped_no_more(self):
        kids = [Child(first_name=f"Kid{i}", date_of_birth=date(2010, 1, 1)) for i in range(16)]

        xml = build_est_xml(_make_user(), _make_filing(), [], children=kids, hersteller_id="12345")

        assert xml.count("<Kind>") == 14
        assert "Kid14" not in xml
        assert "Kid15" not in xml

    def test_no_sa_block_when_no_donations(self):
        xml = build_est_xml(_make_user(), _make_filing(), [], hersteller_id="12345")
        assert "<SA>" not in xml

    def test_no_sa_block_when_deductions_are_non_donation_categories(self):
        deductions = [
            Deduction(category=DeductionCategory.COMMUTE, details={"distance_km": 20, "days_worked": 200}),
            Deduction(category=DeductionCategory.HOME_OFFICE, details={"days_claimed": 100}),
        ]
        xml = build_est_xml(_make_user(), _make_filing(), [], deductions=deductions, hersteller_id="12345")
        assert "<SA>" not in xml

    def test_donations_aggregate_across_rows_into_one_domestic_total(self):
        deductions = [
            Deduction(category=DeductionCategory.DONATIONS, details={"amount_donated_cents": 30_000}),
            Deduction(category=DeductionCategory.DONATIONS, details={"amount_donated_cents": 20_075}),
            # A non-donation row in the same list must not contaminate the total.
            Deduction(category=DeductionCategory.COMMUTE, details={"distance_km": 10, "days_worked": 100}),
        ]

        xml = build_est_xml(_make_user(), _make_filing(), [], deductions=deductions, hersteller_id="12345")

        assert "<SA><Zuw><Sp_MB><Foerd_st_beg_Zw_Inl><Sum_Best>" in xml
        assert "<E0108105>500</E0108105>" in xml  # (30000+20075)/100 truncated to whole euros
        assert "Foerd_st_beg_Zw_EU_EWR" not in xml  # domestic only -- never assumed foreign

    def test_capital_income_aggregates_across_institutions(self):
        stmts = [
            CapitalIncomeStatement(
                institution_name="Trade Republic",
                gross_income_cents=150_000,
                kapitalertragsteuer_withheld_cents=25_000,
                solidarity_surcharge_withheld_cents=1_375,
                church_tax_withheld_cents=0,
            ),
            CapitalIncomeStatement(
                institution_name="DKB",
                gross_income_cents=50_075,
                kapitalertragsteuer_withheld_cents=5_000,
                solidarity_surcharge_withheld_cents=275,
                church_tax_withheld_cents=0,
            ),
        ]

        xml = build_est_xml(
            _make_user(church_tax_type=ChurchTaxType.NONE),
            _make_filing(),
            [],
            capital_income_statements=stmts,
            hersteller_id="12345",
        )

        # Institution names never appear -- the real schema has no
        # per-institution breakdown here, only one combined total.
        assert "Trade Republic" not in xml
        assert "DKB" not in xml
        assert "<Person>PersonA</Person>" in xml
        assert "<E1900701>2000</E1900701>" in xml  # (150000+50075)/100 truncated to whole euros
        assert "<E1904701>300,00</E1904701>" in xml  # Kapitalertragsteuer
        assert "<E1904901>16,50</E1904901>" in xml  # Soli
        assert "<E1904801>0,00</E1904801>" in xml  # Kirchensteuer zur KapESt

    def test_kist_pfl_flag_only_when_church_tax_liable_and_nothing_withheld(self):
        stmt_none_withheld = CapitalIncomeStatement(
            institution_name="Bank", gross_income_cents=10_000, church_tax_withheld_cents=0
        )
        xml = build_est_xml(
            _make_user(church_tax_type=ChurchTaxType.ROEMISCH_KATHOLISCH),
            _make_filing(),
            [],
            capital_income_statements=[stmt_none_withheld],
            hersteller_id="12345",
        )
        assert "<E1900601>1</E1900601>" in xml  # Ja1BaseCType -- "1", not "X"

        stmt_withheld = CapitalIncomeStatement(
            institution_name="Bank", gross_income_cents=10_000, church_tax_withheld_cents=50
        )
        xml = build_est_xml(
            _make_user(church_tax_type=ChurchTaxType.ROEMISCH_KATHOLISCH),
            _make_filing(),
            [],
            capital_income_statements=[stmt_withheld],
            hersteller_id="12345",
        )
        assert "E1900601" not in xml  # withheld already -- flag doesn't apply

        xml = build_est_xml(
            _make_user(church_tax_type=ChurchTaxType.NONE),
            _make_filing(),
            [],
            capital_income_statements=[stmt_none_withheld],
            hersteller_id="12345",
        )
        assert "E1900601" not in xml  # not church-tax liable at all

    def test_rental_property_maps_address_income_and_expenses(self):
        stmts = [
            RentalPropertyStatement(
                property_address="Musterstraße 1, Berlin",
                gross_rental_income_cents=100_000,
                deductible_expenses_cents=155_000,
            ),
            RentalPropertyStatement(
                property_address="Beispielweg 5, Hamburg",
                gross_rental_income_cents=200_000,
                deductible_expenses_cents=50_000,
            ),
        ]

        xml = build_est_xml(_make_user(), _make_filing(), [], rental_property_statements=stmts, hersteller_id="12345")

        assert xml.count("<Laufende_Nummer_V>") == 2
        assert "<Laufende_Nummer_V>1</Laufende_Nummer_V>" in xml
        assert "<Laufende_Nummer_V>2</Laufende_Nummer_V>" in xml
        assert "<E0700407>Musterstraße 1, Berlin</E0700407>" in xml
        assert "<E0700407>Beispielweg 5, Hamburg</E0700407>" in xml
        assert "<E0700206>1000</E0700206>" in xml  # first property's rent, whole euros
        assert "<E0705607>1550</E0705607>" in xml  # first property's expenses, whole euros
        assert "<E0700206>2000</E0700206>" in xml
        assert "<E0705607>500</E0705607>" in xml

    def test_self_employment_maps_business_name_and_net_profit(self):
        stmt = SelfEmploymentStatement(
            business_name="Muster Freelancing", gross_revenue_cents=500_000, deductible_expenses_cents=300_000
        )

        xml = build_est_xml(
            _make_user(), _make_filing(), [], self_employment_statements=[stmt], hersteller_id="12345"
        )

        assert "<Person>PersonA</Person>" in xml
        assert "<E0803101>Muster Freelancing</E0803101>" in xml
        assert "<E0803202>2000</E0803202>" in xml  # net profit (5000-3000), whole euros

    def test_self_employment_caps_at_two_freiber_t_entries(self):
        stmts = [
            SelfEmploymentStatement(
                business_name=f"Business {i}", gross_revenue_cents=100_000, deductible_expenses_cents=0
            )
            for i in range(3)
        ]

        xml = build_est_xml(
            _make_user(), _make_filing(), [], self_employment_statements=stmts, hersteller_id="12345"
        )

        assert xml.count("<Freiber_T>") == 2
        assert "Business 2" not in xml

    def test_no_calculated_tax_figures_are_serialized(self):
        # The real E10 schema has no "computed tax" element at all -- ERiC/
        # the Finanzamt compute the assessment from declared income.
        filing = _make_filing(
            taxable_income_cents=43_680_00, income_tax_cents=8_708_00, solidarity_surcharge_cents=100_00
        )

        xml = build_est_xml(_make_user(), filing, [], hersteller_id="12345")

        assert "Berechnung" not in xml
        assert "8708" not in xml

    def test_finanzamt_bufa_nummer_included_when_supplied(self):
        xml = build_est_xml(
            _make_user(), _make_filing(), [], hersteller_id="12345", finanzamt_bufa_nummer="9181"
        )
        assert '<Empfaenger id="F">9181</Empfaenger>' in xml

    def test_finanzamt_bufa_nummer_omitted_when_not_supplied(self):
        xml = build_est_xml(_make_user(), _make_filing(), [], hersteller_id="12345")
        assert 'id="F"' not in xml

    def test_ziel_bundesland_maps_from_residence_state(self):
        xml = build_est_xml(
            _make_user(residence_state=FederalState.BAYERN), _make_filing(), [], hersteller_id="12345"
        )
        assert '<Empfaenger id="L"><Ziel>BY</Ziel></Empfaenger>' in xml


class TestCentsToEuroStr:
    def test_positive_cents(self):
        # Comma decimal separator -- confirmed required by the real
        # DezimalzahlXxx regex facets, see xml_builder.py's docstring.
        assert _cents_to_euro_str(150_000) == "1500,00"

    def test_negative_cents_keeps_correct_magnitude(self):
        assert _cents_to_euro_str(-55_000) == "-550,00"

    def test_none_defaults_to_zero(self):
        assert _cents_to_euro_str(None) == "0,00"


class TestCentsToWholeEuroStr:
    def test_truncates_cents_not_rounds(self):
        assert _cents_to_whole_euro_str(1500_99) == "1500"

    def test_negative_cents_keeps_correct_magnitude(self):
        assert _cents_to_whole_euro_str(-550_99) == "-550"

    def test_none_defaults_to_zero(self):
        assert _cents_to_whole_euro_str(None) == "0"


class TestStubEricClient:
    def test_validates_well_formed_elster_xml(self):
        client = StubEricClient()
        xml = build_est_xml(_make_user(), _make_filing(), [], hersteller_id="12345")
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
        xml = build_est_xml(_make_user(), _make_filing(), [], hersteller_id="12345")

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
