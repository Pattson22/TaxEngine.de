"""
Builds the XML payload handed to ERiC for validation/submission.

Field codes and structure below are sourced from the real ERiC 44.2.4.1
SDK's E10 schema (`Dokumentation/Datenarten/ElsterErklaerung/ESt/Schema/2024/
E10-2024.xsd`) and its own worked example (`.../ESt/Beispiele/est_e10_2024.xml`),
obtained via ELSTER Developer Area access (see docs/ELSTER_ERIC_INTEGRATION.md)
-- not guessed. Every `E0######` element name below is a direct, verified copy
of a real field identifier, cross-checked against the schema's own
`<xs:documentation>` annotation for that field.

## What's mapped to the real schema so far
- The transfer envelope (`TransferHeader`/`NutzdatenHeader`/`Datei`),
  matching the general Elster header schema
  (`ElsterBasisSchema/Schema/th000011_extern.xsd`).
- `ESt1A` (Mantelbogen): the declaration-type flag (`Art_Erkl`/E0100001),
  the primary filer's personal data (`Allg/A`), the joint-assessment flag
  (`Allg/Vlg_Art`), and the spouse's personal data (`Allg/B`) when filing
  jointly.
- `S` (Anlage S, selbständige Arbeit): one `<S>` block for the primary
  filer with up to 2 `Gewinn/Freiber_T` entries (the schema's own
  `maxOccurs`), each the net profit for one `self_employment_statements`
  row. Deliberately `S` (§18 EStG, freiberufliche/selbständige Arbeit),
  not `G` (§15 EStG, Gewerbebetrieb) -- `tax_engine/self_employment_income.py`'s
  own docstring already states its (Gewerbesteuer-free) math is "correct
  for freelancers/liberal professions", so `S` is the schema element that
  actually matches what this project computes, not a coin flip between
  the two. Only the aggregated net profit is submitted here -- a detailed
  Einnahmen-Überschuss-Rechnung (revenue/expense line items) is a
  SEPARATE Datenart (`EUER`) this project doesn't build or submit.
- `N` (Anlage N, employee wage income): one `<N>` block for the primary
  filer with an `LStB_1_5_Einz` entry per `wage_tax_certificates` row plus
  the aggregated `LStB_1_5_Sum` that's what ERiC/the Finanzamt actually
  reads as the declared total.
- `KAP` (Anlage KAP, capital income): one `<KAP>` block for the primary
  filer with the aggregated gross Kapitalerträge
  (`KapErt_inl_StAbz/Betr_lt_StBesch/E1900701`) and withheld
  Kapitalertragsteuer/Soli/Kirchensteuer
  (`St_Abz_Betr_Inl_u_Inv_Ert`) summed across all
  `capital_income_statements` rows -- the real schema has no per-institution
  breakdown here (that stays in the taxpayer's own Steuerbescheinigungen),
  only one combined total per box, same shape as `N`'s `LStB_1_5_Sum`.
- `V` (Anlage V, rental income -- note the real tag is `V`, nothing like
  the old illustrative `VermietungUndVerpachtung`): one `<V>` block per
  `rental_property_statements` row (the schema's own per-property
  cardinality, via `Laufende_Nummer_V`), with the property's address
  (`Allg/Lage/E0700407`), total rent (`Einn/Mieteinn/Whg/Sum/E0700206`),
  and total deductible costs filed under the schema's generic "Sonstige
  Werbungskosten" bucket (`Wk/Sonst/Sum/E0705607`) -- NOT under a specific
  category like AfA depreciation or mortgage interest, since
  `rental_income.py`'s own docstring already states this project doesn't
  compute an AfA schedule, and claiming one of the specific boxes would
  misrepresent an expense type this project never actually determined.
- `Kind` (Anlage Kind): one `<Kind>` block per `app.models.child.Child`
  row (a separate table from `filing.number_of_children` -- see that
  model's own docstring for why the two are deliberately independent),
  with the child's identity (`Ang_Kind/Allg`: Identifikationsnummer, Vor-
  and, if different from the filer's, Nachname, Geburtsdatum) and
  Kindschaftsverhältnis (`K_Verh/K_Verh_A`, and `K_Verh_B` too when filing
  jointly, both under the SAME simplifying assumption as the rest of this
  module: the child lived with the family, and that relationship existed,
  for the full calendar year -- no partial-year modeling, matching
  `kinderfreibetrag.py`'s own documented scope limitation).
- `SA` (Sonderausgaben), donations only: `Zuw/Sp_MB/Foerd_st_beg_Zw_Inl`
  carries the combined total across every DONATIONS-category `deductions`
  row for the year (`Sum_Best/E0108105`), aggregated with the exact same
  rule as `tax_calculation_service._aggregate_donations_this_year` (the
  20% cap applies to the SUM, not per-row -- see that function's own
  docstring for the real bug this once caught). Always filed as
  `Foerd_st_beg_Zw_Inl` (domestic recipients) -- the data model doesn't
  collect a recipient organization or country, so foreign-recipient
  donations (`Foerd_st_beg_Zw_EU_EWR`) can never be distinguished and are
  never assumed.

## What's deliberately NOT mapped yet -- omitted, not guessed
- `SA/KiSt` (church tax PAID, e.g. direct quarterly payments to the
  Kirchensteueramt): its own field documentation is explicit that this
  box excludes "soweit diese ... als Zuschlag zur Abgeltungsteuer
  einbehalten oder gezahlt wurde" (church tax already withheld as a
  capital-gains surcharge) -- i.e. it's legally a DIFFERENT figure from
  the church tax `N`/`KAP` already declare as withheld, not a
  restatement of it. This project doesn't collect "church tax paid
  directly, outside withholding" anywhere, and deriving this box from
  the withheld figures already declared elsewhere would misrepresent
  what it means -- so it's left out rather than guessed at.
- The KOMPRIMIERT cover-sheet block (`Vorsatz`) needs the filer's
  Steuernummer in ERiC's own unified 13-digit format, which the real API
  provides via `EricMakeElsterStnr()` -- not yet bound in
  `native_bindings.py` (only the subset of the API this project's
  KOMPRIMIERT-unauthenticated flow needs is declared there today) -- so
  this Anlage is real, separate research/implementation work, not a
  drive-by addition.

There is also no "computed tax" element in the real E10 schema at all --
ERiC/the Finanzamt compute the assessment FROM the declared income; a
filer never submits their own calculated `Einkommensteuer`/
`Solidaritaetszuschlag`/etc. This is why `filing`'s calculated fields
(`taxable_income_cents`, `income_tax_cents`, ...) are no longer serialized
anywhere below, unlike the old illustrative version of this file's
fabricated `<Berechnung>` block.

Two known gaps block ever pointing this at a real endpoint, tracked
separately from field-code correctness, and both CONFIRMED by actually
running generated output through the real EricCheckXML() (not assumed):
- `HerstellerID` (BZSt-issued once this project registers as a software
  manufacturer -- see docs/ELSTER_ERIC_INTEGRATION.md) must be supplied
  by the caller; there is no valid default.
- The filer's Finanzamt BuFa-Nummer (`NutzdatenHeader`'s
  `Empfaenger id="F"`) isn't collected anywhere in the data model yet.
  `finanzamt_bufa_nummer` is accepted as optional and simply omitted if
  not supplied, BUT EricCheckXML() rejects a `NutzdatenHeader` missing it
  outright ("missing elements in content model") -- it is a hard
  requirement of the real schema, not just supplementary routing data, so
  no XML built without it will ever pass real validation.

Uses stdlib `xml.etree.ElementTree` (not manual string formatting) so
user-supplied text (names, addresses) is correctly XML-escaped rather than
risking injection/malformed output.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from app.models.capital_income_statement import CapitalIncomeStatement
from app.models.child import Child
from app.models.deduction import Deduction
from app.models.enums import ChildRelationshipType, ChurchTaxType, DeductionCategory, FederalState, TaxClass
from app.models.rental_property_statement import RentalPropertyStatement
from app.models.self_employment_statement import SelfEmploymentStatement
from app.models.tax_filing import TaxFiling
from app.models.user import User
from app.models.wage_tax_certificate import WageTaxCertificate
from app.schemas.deduction import DonationDetails

_ELSTER_NAMESPACE = "http://www.elster.de/elsterxml/schema/v11"
_HEADER_VERSION = "11"

# headerbasis:BundeslandSType (ElsterBasisSchema/Schema/headerbasis_datentypen.xsd)
# -- TransferHeader's Empfaenger id="L" target Bundesland code.
_FEDERAL_STATE_TO_ZIEL: dict[FederalState, str] = {
    FederalState.BADEN_WUERTTEMBERG: "BW",
    FederalState.BAYERN: "BY",
    FederalState.BERLIN: "BE",
    FederalState.BRANDENBURG: "BB",
    FederalState.BREMEN: "HB",
    FederalState.HAMBURG: "HH",
    FederalState.HESSEN: "HE",
    FederalState.MECKLENBURG_VORPOMMERN: "MV",
    FederalState.NIEDERSACHSEN: "NI",
    FederalState.NORDRHEIN_WESTFALEN: "NW",
    FederalState.RHEINLAND_PFALZ: "RP",
    FederalState.SAARLAND: "SL",
    FederalState.SACHSEN: "SN",
    FederalState.SACHSEN_ANHALT: "ST",
    FederalState.SCHLESWIG_HOLSTEIN: "SH",
    FederalState.THUERINGEN: "TH",
}

# Enum_Religionsschluessel_ab_VZ_2014_3_BaseCType -- only the three values
# this project's ChurchTaxType enum maps to UNAMBIGUOUSLY. ChurchTaxType.OTHER
# covers many distinct real denominations (each its own code, e.g. "05"
# Evangelisch-reformiert, "07" Französisch-reformiert, ...) that a single
# "OTHER" bucket can't be resolved to one code without guessing -- so it's
# deliberately left unmapped (the field is simply omitted) rather than risk
# declaring the wrong religious community to the Finanzamt.
_CHURCH_TAX_TYPE_TO_RELIGIONSSCHLUESSEL: dict[ChurchTaxType, str] = {
    ChurchTaxType.NONE: "11",
    ChurchTaxType.ROEMISCH_KATHOLISCH: "03",
    ChurchTaxType.EVANGELISCH: "02",
}

# Enum_N_ArbL_LStB_1_5_Sum_E0200002_CType -- Steuerklasse I-VI as ERiC's "1".."6".
_TAX_CLASS_TO_STEUERKLASSE: dict[TaxClass, str] = {
    TaxClass.I: "1",
    TaxClass.II: "2",
    TaxClass.III: "3",
    TaxClass.IV: "4",
    TaxClass.V: "5",
    TaxClass.VI: "6",
}

# Enum_Kind_K_Verh_K_Verh_A_E0500807_CType (and the identical _B_E0500808
# variant) -- the real 3-value Art des Kindschaftsverhältnisses enum.
_CHILD_RELATIONSHIP_TYPE_TO_KINDSCHAFTSVERHAELTNIS: dict[ChildRelationshipType, str] = {
    ChildRelationshipType.BIOLOGICAL_OR_ADOPTED: "1",
    ChildRelationshipType.FOSTER: "2",
    ChildRelationshipType.GRANDCHILD_OR_STEP: "3",
}

# WS/Inl's E0500703 and K_Verh_A/B's E0500601/E0500805 are all
# DatumBereichTTpMMbTTpMMBaseCType ("TT.MM-TT.MM", day.month only, no
# year) date RANGES -- this module's full-calendar-year simplification
# (see module docstring) always uses this same full-year range.
_FULL_YEAR_RANGE = "01.01-31.12"


def _cents_to_euro_str(cents: int | None) -> str:
    """Most of ERiC's numeric fields are decimal strings with 2 fraction
    digits, not cents -- and, confirmed against the real DezimalzahlXxx
    types' regex facets AND by actually running this through the real
    EricCheckXML() (see xml_builder's module docstring), the decimal
    separator is a COMMA, matching German number formatting
    ("67554,76"), not a period. A period is silently a schema violation,
    not just a style choice.

    Signed values (e.g. a rental loss) need the sign handled separately
    from the magnitude -- `divmod` on a negative number floors toward
    negative infinity, which would silently mangle it (e.g. -550 cents ->
    "-6,50" instead of "-5,50").
    """
    if cents is None:
        cents = 0
    sign = "-" if cents < 0 else ""
    euros, remainder = divmod(abs(cents), 100)
    return f"{sign}{euros},{remainder:02d}"


def _cents_to_whole_euro_str(cents: int | None) -> str:
    """LStB_1_5_Sum's Bruttoarbeitslohn (E0200201) is typed
    `GanzzahlOhneFuehrNull` (whole euros, no fraction digits, so no
    decimal separator either) in the real schema -- unlike LStB_1_5_Einz's
    E0200204, which is a 2-decimal `Dezimalzahl`. Cents are truncated,
    matching the paper Lohnsteuerbescheinigung summary convention
    ("Centbeträge werden nicht berücksichtigt"), not rounded.
    """
    if cents is None:
        cents = 0
    sign = "-" if cents < 0 else ""
    euros = abs(cents) // 100
    return f"{sign}{euros}"


def _sub(parent: ET.Element, tag: str, text: str | None) -> ET.Element | None:
    """SubElement helper that omits the element entirely when there's no
    value, rather than emitting an empty tag -- every field this module
    writes is `minOccurs="0"` in the real schema, so "absent" is always a
    valid, meaningful choice ERiC/the Finanzamt already handle."""
    if text is None or text == "":
        return None
    element = ET.SubElement(parent, tag)
    element.text = text
    return element


def build_est_xml(
    user: User,
    filing: TaxFiling,
    wage_certs: list[WageTaxCertificate],
    capital_income_statements: list[CapitalIncomeStatement] | None = None,
    rental_property_statements: list[RentalPropertyStatement] | None = None,
    self_employment_statements: list[SelfEmploymentStatement] | None = None,
    children: list[Child] | None = None,
    deductions: list[Deduction] | None = None,
    *,
    hersteller_id: str,
    finanzamt_bufa_nummer: str | None = None,
) -> str:
    """Serialize one user/filing's real-schema-mapped data into the E10 XML
    payload for an ESt submission -- see this module's docstring for
    exactly what is and isn't mapped yet.

    Args:
        user: the taxpayer -- must have `tax_identification_number` set
            (ERiC requires the Steuer-ID; a real submission_service caller
            should validate this before calling here, this function does
            not re-validate it).
        filing: the filing being submitted. Only `tax_year` and
            `tax_class`/`is_joint_assessment` (via `user`) drive the XML
            now -- its calculated fields are NOT serialized, see this
            module's docstring for why.
        wage_certs: this filing's wage_tax_certificates rows (Anlage N).
        capital_income_statements: this filing's capital_income_statements
            rows (Anlage KAP) -- aggregated into one total, see this
            module's docstring.
        rental_property_statements: this filing's rental_property_statements
            rows (Anlage V) -- one `<V>` block each.
        self_employment_statements: this filing's self_employment_statements
            rows (Anlage S) -- up to 2 (the real schema's own limit for
            this simplified path), see this module's docstring.
        children: this user's `children` rows for `filing.tax_year`
            (Anlage Kind) -- one `<Kind>` block each, up to 14 (the real
            schema's own limit). Independent of `filing.number_of_children`,
            which still drives the Günstigerprüfung calculation itself --
            see `app.models.child.Child`'s docstring for why.
        deductions: this filing's deductions rows -- only DONATIONS-category
            rows are used (Anlage SA's `Zuw/Sp_MB/Foerd_st_beg_Zw_Inl`,
            aggregated exactly like `_aggregate_donations_this_year` in
            `tax_calculation_service.py`); every other category is not yet
            mapped, see this module's docstring.
        hersteller_id: BZSt-issued manufacturer id (required by the real
            TransferHeader schema, no valid default -- see
            docs/ELSTER_ERIC_INTEGRATION.md for the registration status).
        finanzamt_bufa_nummer: the filer's Finanzamt's 4-digit
            Bundesfinanzamtsnummer, if known -- not currently collected
            anywhere in the data model, so omitted (no `Empfaenger id="F"`)
            when not supplied.

    Returns:
        A UTF-8 XML string. Still needs `EricClient.validate_xml()` --
        this function does not validate against the real schema itself.
    """
    capital_income_statements = capital_income_statements or []
    rental_property_statements = rental_property_statements or []
    self_employment_statements = self_employment_statements or []
    children = children or []
    deductions = deductions or []

    root = ET.Element("Elster", xmlns=_ELSTER_NAMESPACE)

    header = ET.SubElement(root, "TransferHeader", version=_HEADER_VERSION)
    ET.SubElement(header, "Verfahren").text = "ElsterErklaerung"
    ET.SubElement(header, "DatenArt").text = "ESt"
    ET.SubElement(header, "Vorgang").text = "send-NoSig"  # unauthenticated -- see ELSTER_ERIC_INTEGRATION.md section 6

    ziel = _FEDERAL_STATE_TO_ZIEL.get(user.residence_state)
    if ziel:
        empfaenger_l = ET.SubElement(header, "Empfaenger", id="L")
        ET.SubElement(empfaenger_l, "Ziel").text = ziel

    ET.SubElement(header, "HerstellerID").text = hersteller_id
    ET.SubElement(header, "DatenLieferant").text = "TaxEngine.de"

    datei = ET.SubElement(header, "Datei")
    ET.SubElement(datei, "Verschluesselung").text = "CMSEncryptedData"
    ET.SubElement(datei, "Kompression").text = "GZIP"
    ET.SubElement(datei, "TransportSchluessel")

    daten_teil = ET.SubElement(root, "DatenTeil")
    nutzdatenblock = ET.SubElement(daten_teil, "Nutzdatenblock")

    nutzdaten_header = ET.SubElement(nutzdatenblock, "NutzdatenHeader", version=_HEADER_VERSION)
    # NutzdatenTicket has maxLength=32 -- a dashed UUID string is 36 chars
    # and is rejected by EricCheckXML(); .hex is exactly 32.
    ET.SubElement(nutzdaten_header, "NutzdatenTicket").text = filing.id.hex
    if finanzamt_bufa_nummer:
        ET.SubElement(nutzdaten_header, "Empfaenger", id="F").text = finanzamt_bufa_nummer

    nutzdaten = ET.SubElement(nutzdatenblock, "Nutzdaten")
    e10 = ET.SubElement(
        nutzdaten,
        "E10",
        xmlns=f"http://finkonsens.de/elster/elstererklaerung/est/e10/v{filing.tax_year}",
        version=str(filing.tax_year),
    )

    est1a = ET.SubElement(e10, "ESt1A")

    art_erkl = ET.SubElement(est1a, "Art_Erkl")
    ET.SubElement(art_erkl, "E0100001").text = "X"  # Einkommensteuererklärung -- always true here

    allg = ET.SubElement(est1a, "Allg")
    a = ET.SubElement(allg, "A")
    _sub(a, "E0100081", user.tax_identification_number)  # Identifikationsnummer
    _sub(a, "E0100401", _format_date(user.date_of_birth))  # Geburtsdatum
    _sub(a, "E0100201", user.last_name)  # Name
    _sub(a, "E0100301", user.first_name)  # Vorname
    religionsschluessel = _CHURCH_TAX_TYPE_TO_RELIGIONSSCHLUESSEL.get(user.church_tax_type)
    _sub(a, "E0100402", religionsschluessel)  # Religion
    _sub(a, "E0101104", user.street)  # Straße (derzeitige Adresse)
    _sub(a, "E0101206", user.house_number)  # Hausnummer
    _sub(a, "E0100601", user.postal_code)  # Postleitzahl (Inland)
    _sub(a, "E0100602", user.city)  # Wohnort

    spouse = user.spouse if user.is_joint_assessment else None
    if user.is_joint_assessment:
        vlg_art = ET.SubElement(allg, "Vlg_Art")
        ET.SubElement(vlg_art, "E0101201").text = "X"  # Zusammenveranlagung

    if spouse is not None:
        b = ET.SubElement(allg, "B")
        _sub(b, "E0100082", spouse.tax_identification_number)  # Identifikationsnummer
        _sub(b, "E0101001", _format_date(spouse.date_of_birth))  # Geburtsdatum
        _sub(b, "E0100901", spouse.last_name)  # Name
        _sub(b, "E0100801", spouse.first_name)  # Vorname
        spouse_religionsschluessel = _CHURCH_TAX_TYPE_TO_RELIGIONSSCHLUESSEL.get(spouse.church_tax_type)
        _sub(b, "E0101002", spouse_religionsschluessel)  # Religion

    # Mirrors tax_calculation_service._aggregate_donations_this_year exactly
    # (same DonationDetails schema, same "combined total across every
    # DONATIONS row" rule -- the 20% cap applies to the sum, not per-row).
    total_donations_cents = 0
    for deduction in deductions:
        if deduction.category != DeductionCategory.DONATIONS:
            continue
        total_donations_cents += DonationDetails.model_validate(deduction.details).amount_donated_cents

    if total_donations_cents > 0:
        sa = ET.SubElement(e10, "SA")
        zuw = ET.SubElement(sa, "Zuw")
        sp_mb = ET.SubElement(zuw, "Sp_MB")
        # Foerd_st_beg_Zw_Inl = donations to DOMESTIC tax-privileged
        # recipients -- the general-purpose donation box, and the only one
        # this project's data model can support (no recipient
        # country/organization is collected, so foreign-recipient
        # donations -- Foerd_st_beg_Zw_EU_EWR -- can't be distinguished
        # and are never assumed). SA/KiSt (church tax PAID directly, not
        # withheld) is deliberately NOT mapped -- see this module's
        # docstring.
        foerd_inl = ET.SubElement(sp_mb, "Foerd_st_beg_Zw_Inl")
        sum_best = ET.SubElement(foerd_inl, "Sum_Best")
        ET.SubElement(sum_best, "E0108105").text = _cents_to_whole_euro_str(
            total_donations_cents
        )  # zur Förderung steuerbegünstigter Zwecke an Empfänger im Inland

    # Kind's real maxOccurs is 14 -- one <Kind> block per child, not
    # aggregated like N/KAP's per-source totals.
    for child in children[:14]:
        kind = ET.SubElement(e10, "Kind")

        ang_kind = ET.SubElement(kind, "Ang_Kind")
        allg_kind = ET.SubElement(ang_kind, "Allg")
        _sub(allg_kind, "E0500406", child.tax_identification_number)  # Identifikationsnummer
        _sub(allg_kind, "E0500107", child.first_name)  # Vorname
        _sub(allg_kind, "E0500108", child.last_name)  # ggf. abweichender Familienname
        _sub(allg_kind, "E0500701", _format_date(child.date_of_birth))  # Geburtsdatum
        ws = ET.SubElement(ang_kind, "WS")
        inl = ET.SubElement(ws, "Inl")
        # Full calendar year -- see module docstring's simplification note.
        ET.SubElement(inl, "E0500703").text = _FULL_YEAR_RANGE

        # `or` guards against an unflushed Child whose column DEFAULT
        # hasn't been applied yet (SQLAlchemy only applies a mapped_column
        # default at flush/INSERT, not on a bare Python object) -- the same
        # real crash risk already handled for the numeric `or 0` guards
        # above, here for an enum instead of a number.
        relationship_type = child.relationship_type or ChildRelationshipType.BIOLOGICAL_OR_ADOPTED
        kindschaftsverhaeltnis = _CHILD_RELATIONSHIP_TYPE_TO_KINDSCHAFTSVERHAELTNIS[relationship_type]
        k_verh = ET.SubElement(kind, "K_Verh")
        k_verh_a = ET.SubElement(k_verh, "K_Verh_A")
        ET.SubElement(k_verh_a, "E0500807").text = kindschaftsverhaeltnis
        ET.SubElement(k_verh_a, "E0500601").text = _FULL_YEAR_RANGE
        if spouse is not None:
            # Simplifying assumption: a jointly-assessed child is treated
            # as related to BOTH spouses the same way -- no modeling of a
            # stepchild who's only related to one of them.
            k_verh_b = ET.SubElement(k_verh, "K_Verh_B")
            ET.SubElement(k_verh_b, "E0500808").text = kindschaftsverhaeltnis
            ET.SubElement(k_verh_b, "E0500805").text = _FULL_YEAR_RANGE

    if self_employment_statements:
        s = ET.SubElement(e10, "S")
        ET.SubElement(s, "Person").text = "PersonA"
        gewinn = ET.SubElement(s, "Gewinn")
        # Freiber_T's real maxOccurs is 2 -- more than 2 self-employment
        # rows for one filer isn't representable in this Anlage today.
        for stmt in self_employment_statements[:2]:
            freiber_t = ET.SubElement(gewinn, "Freiber_T")
            _sub(freiber_t, "E0803101", stmt.business_name)  # genaue Berufsbezeichnung oder Tätigkeit
            net_profit_cents = (stmt.gross_revenue_cents or 0) - (stmt.deductible_expenses_cents or 0)
            ET.SubElement(freiber_t, "E0803202").text = _cents_to_whole_euro_str(net_profit_cents)  # Betrag

    if wage_certs:
        n = ET.SubElement(e10, "N")
        ET.SubElement(n, "Person").text = "PersonA"
        arb_l = ET.SubElement(n, "ArbL")

        for cert in wage_certs:
            einz = ET.SubElement(arb_l, "LStB_1_5_Einz")
            ET.SubElement(einz, "E0200204").text = _cents_to_euro_str(cert.gross_wage_cents)  # Bruttoarbeitslohn
            ET.SubElement(einz, "E0200304").text = _cents_to_euro_str(cert.income_tax_withheld_cents)  # Lohnsteuer
            ET.SubElement(einz, "E0200404").text = _cents_to_euro_str(
                cert.solidarity_surcharge_cents
            )  # Solidaritätszuschlag
            ET.SubElement(einz, "E0200504").text = _cents_to_euro_str(
                cert.church_tax_withheld_cents
            )  # Kirchensteuer des Arbeitnehmers

        total_gross_wage = sum(cert.gross_wage_cents or 0 for cert in wage_certs)
        total_income_tax = sum(cert.income_tax_withheld_cents or 0 for cert in wage_certs)
        total_soli = sum(cert.solidarity_surcharge_cents or 0 for cert in wage_certs)
        total_church_tax = sum(cert.church_tax_withheld_cents or 0 for cert in wage_certs)

        sum_block = ET.SubElement(arb_l, "LStB_1_5_Sum")
        steuerklasse = _TAX_CLASS_TO_STEUERKLASSE.get(user.tax_class)
        _sub(sum_block, "E0200002", steuerklasse)  # Steuerklasse
        ET.SubElement(sum_block, "E0200201").text = _cents_to_whole_euro_str(total_gross_wage)  # Bruttoarbeitslohn
        ET.SubElement(sum_block, "E0200301").text = _cents_to_euro_str(total_income_tax)  # Lohnsteuer
        ET.SubElement(sum_block, "E0200401").text = _cents_to_euro_str(total_soli)  # Solidaritätszuschlag
        ET.SubElement(sum_block, "E0200501").text = _cents_to_euro_str(
            total_church_tax
        )  # Kirchensteuer des Arbeitnehmers

    if capital_income_statements:
        kap = ET.SubElement(e10, "KAP")
        ET.SubElement(kap, "Person").text = "PersonA"

        # `or 0` guards against an unflushed statement whose NOT NULL
        # DEFAULT 0 columns haven't been applied yet (SQLAlchemy only
        # applies server_default at INSERT, not on a bare Python object) --
        # a real crash risk here, not a defensive-programming nicety, since
        # this function must also work on rows a caller just constructed.
        total_kap_church_tax = sum(stmt.church_tax_withheld_cents or 0 for stmt in capital_income_statements)
        # E1900601's real documentation is the SPECIFIC scenario "I am
        # church-tax liable and earned capital income from which
        # Kapitalertragsteuer, but no Kirchensteuer, was withheld" -- not a
        # general "are you church-tax liable" flag, so it's only set when
        # that precise condition holds (liable overall, nothing withheld
        # at source here).
        if user.church_tax_type != ChurchTaxType.NONE and total_kap_church_tax == 0:
            kist_pfl = ET.SubElement(kap, "KiSt_Pfl")
            # E1900601 is typed Ja1BaseCType -- valid value is "1", NOT "X"
            # (unlike Art_Erkl/Vlg_Art's JaXBaseCType checkboxes above) --
            # confirmed by actually running "X" through EricCheckXML() and
            # getting a real "value 'X' not in enumeration" rejection.
            ET.SubElement(kist_pfl, "E1900601").text = "1"

        total_gross_kap_income = sum(stmt.gross_income_cents or 0 for stmt in capital_income_statements)
        kap_ert_inl = ET.SubElement(kap, "KapErt_inl_StAbz")
        betr_lt_stbesch = ET.SubElement(kap_ert_inl, "Betr_lt_StBesch")
        ET.SubElement(betr_lt_stbesch, "E1900701").text = _cents_to_whole_euro_str(
            total_gross_kap_income
        )  # Kapitalerträge

        total_kapest = sum(stmt.kapitalertragsteuer_withheld_cents or 0 for stmt in capital_income_statements)
        total_kap_soli = sum(stmt.solidarity_surcharge_withheld_cents or 0 for stmt in capital_income_statements)
        st_abz = ET.SubElement(kap, "St_Abz_Betr_Inl_u_Inv_Ert")
        ET.SubElement(st_abz, "E1904701").text = _cents_to_euro_str(total_kapest)  # Kapitalertragsteuer
        ET.SubElement(st_abz, "E1904901").text = _cents_to_euro_str(total_kap_soli)  # Solidaritätszuschlag
        ET.SubElement(st_abz, "E1904801").text = _cents_to_euro_str(
            total_kap_church_tax
        )  # Kirchensteuer zur Kapitalertragsteuer

    for index, stmt in enumerate(rental_property_statements, start=1):
        v = ET.SubElement(e10, "V")
        ET.SubElement(v, "Laufende_Nummer_V").text = str(index)  # 1st/2nd/... Anlage V

        allg_v = ET.SubElement(v, "Allg")
        lage = ET.SubElement(allg_v, "Lage")
        ET.SubElement(lage, "E0700407").text = stmt.property_address  # Straße, Hausnummer (combined field)

        einn = ET.SubElement(v, "Einn")
        whg = ET.SubElement(ET.SubElement(einn, "Mieteinn"), "Whg")
        whg_sum = ET.SubElement(whg, "Sum")
        ET.SubElement(whg_sum, "E0700206").text = _cents_to_whole_euro_str(
            stmt.gross_rental_income_cents
        )  # Summe Mieteinnahmen

        wk = ET.SubElement(v, "Wk")
        # Filed under the schema's generic "Sonstiges" bucket, not a
        # specific category like AfA/Schuldzinsen -- see this module's
        # docstring for why claiming a specific one would be dishonest.
        sonst_sum = ET.SubElement(ET.SubElement(wk, "Sonst"), "Sum")
        ET.SubElement(sonst_sum, "E0705607").text = _cents_to_whole_euro_str(
            stmt.deductible_expenses_cents
        )  # Abzugsfähige Werbungskosten

    # `encoding="unicode"` makes ElementTree return a str, but it then
    # NEVER emits an XML declaration regardless of `xml_declaration` --
    # confirmed (by actually running output through EricCheckXML, see this
    # module's docstring) that ERiC rejects XML without an explicit
    # `encoding="UTF-8"` declaration ("Die Eingabedaten lagen nicht im
    # Encoding UTF-8 ohne BOM vor oder es war kein Encoding spezifiziert."),
    # so it's prepended manually here to match the SDK's own examples.
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")


def _format_date(value) -> str | None:
    """ERiC's date fields use TT.MM.JJJJ (`DatumTTpMMpJJJJBekanntBaseCType`),
    not ISO 8601."""
    if value is None:
        return None
    return value.strftime("%d.%m.%Y")
