"""
Builds the XML payload handed to ERiC for validation/submission.

*** ILLUSTRATIVE STRUCTURE — NOT THE OFFICIAL SCHEMA ***
The top-level envelope (`TransferHeader` / `DatenTeil` / `Nutzdatenblock`)
mirrors the publicly-documented general shape of the Elster transfer
format used across all Elster data types. The `Steuerfall` payload inside
it, however, is illustrative: the actual field names, ordering, and
required elements for an ESt (Einkommensteuer) submission come from the
Datenartenkatalog, a schema BZSt only distributes to developers who have
signed the ERiC software-developer agreement — this project does not have
access to it. Treat every element below `<Steuerfall>` as a placeholder to
be replaced with the real schema once that access exists; do not transmit
this XML to a real Finanzamt endpoint.

Uses stdlib `xml.etree.ElementTree` (not manual string formatting) so
user-supplied text (names, addresses) is correctly XML-escaped rather than
risking injection/malformed output.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from app.models.capital_income_statement import CapitalIncomeStatement
from app.models.rental_property_statement import RentalPropertyStatement
from app.models.self_employment_statement import SelfEmploymentStatement
from app.models.tax_filing import TaxFiling
from app.models.user import User
from app.models.wage_tax_certificate import WageTaxCertificate

_ELSTER_NAMESPACE = "http://www.elster.de/2002/XMLSchema"


def _cents_to_euro_str(cents: int | None) -> str:
    """ERiC's numeric fields are plain decimal strings, not cents.

    Rental and self-employment income are signed (a loss is a legitimate
    negative value, §2 Abs. 3 EStG) -- `divmod` on a negative number floors
    toward negative infinity, which would silently mangle the sign (e.g.
    -550 cents -> "-6.50" instead of "-5.50"), so the sign is handled
    separately from the magnitude.
    """
    if cents is None:
        cents = 0
    sign = "-" if cents < 0 else ""
    euros, remainder = divmod(abs(cents), 100)
    return f"{sign}{euros}.{remainder:02d}"


def build_est_xml(
    user: User,
    filing: TaxFiling,
    wage_certs: list[WageTaxCertificate],
    capital_income_statements: list[CapitalIncomeStatement] | None = None,
    rental_property_statements: list[RentalPropertyStatement] | None = None,
    self_employment_statements: list[SelfEmploymentStatement] | None = None,
) -> str:
    """Serialize one user/filing plus all of its per-source income rows into
    the (illustrative) XML payload for an ESt submission.

    Args:
        user: the taxpayer -- must have `tax_identification_number` set
            (ERiC requires the Steuer-ID; a real submission_service caller
            should validate this before calling here, this function does
            not re-validate it).
        filing: the CALCULATED/FEE_PAID filing being submitted -- its
            aggregate fields (net_rental_income_cents, capital_gains_tax_cents,
            etc.) are what the calculation engine actually produced, so
            `Berechnung` is sourced from the filing row, not recomputed here.
        wage_certs: this filing's wage_tax_certificates rows.
        capital_income_statements: this filing's capital_income_statements
            rows (Anlage KAP), if any.
        rental_property_statements: this filing's rental_property_statements
            rows (Anlage V), if any.
        self_employment_statements: this filing's self_employment_statements
            rows (Anlage S / EÜR), if any.

    Returns:
        A UTF-8 XML string, NOT yet validated against the real ERiC schema
        (that happens in EricClient.validate_xml).
    """
    capital_income_statements = capital_income_statements or []
    rental_property_statements = rental_property_statements or []
    self_employment_statements = self_employment_statements or []
    root = ET.Element("Elster", xmlns=_ELSTER_NAMESPACE)

    header = ET.SubElement(root, "TransferHeader", version="11")
    ET.SubElement(header, "Verfahren").text = "ElsterErklaerung"
    ET.SubElement(header, "DatenArt").text = "ESt"
    ET.SubElement(header, "Vorgang").text = "send-NoSig"
    ET.SubElement(header, "DatenLieferant").text = "TaxEngine.de"

    daten_teil = ET.SubElement(root, "DatenTeil")
    nutzdatenblock = ET.SubElement(daten_teil, "Nutzdatenblock")

    nutzdaten_header = ET.SubElement(nutzdatenblock, "NutzdatenHeader", version="11")
    ET.SubElement(nutzdaten_header, "NutzdatenTicket").text = str(filing.id)

    nutzdaten = ET.SubElement(nutzdatenblock, "Nutzdaten")
    steuerfall = ET.SubElement(nutzdaten, "Steuerfall")

    steuerpflichtiger = ET.SubElement(steuerfall, "Steuerpflichtiger")
    ET.SubElement(steuerpflichtiger, "SteuerId").text = user.tax_identification_number or ""
    ET.SubElement(steuerpflichtiger, "Name").text = user.last_name
    ET.SubElement(steuerpflichtiger, "Vorname").text = user.first_name

    ET.SubElement(steuerfall, "Veranlagungsjahr").text = str(filing.tax_year)

    einkuenfte = ET.SubElement(steuerfall, "Einkuenfte")
    nichtselbstaendige_arbeit = ET.SubElement(einkuenfte, "NichtselbstaendigeArbeit")
    for cert in wage_certs:
        arbeitgeber = ET.SubElement(nichtselbstaendige_arbeit, "Arbeitgeber")
        ET.SubElement(arbeitgeber, "Name").text = cert.employer_name
        ET.SubElement(arbeitgeber, "Bruttoarbeitslohn").text = _cents_to_euro_str(cert.gross_wage_cents)
        ET.SubElement(arbeitgeber, "EinbehalteneLohnsteuer").text = _cents_to_euro_str(
            cert.income_tax_withheld_cents
        )

    if capital_income_statements:
        kapitalvermoegen = ET.SubElement(einkuenfte, "Kapitalvermoegen")
        for stmt in capital_income_statements:
            institut = ET.SubElement(kapitalvermoegen, "Institut")
            ET.SubElement(institut, "Name").text = stmt.institution_name
            ET.SubElement(institut, "Kapitalertraege").text = _cents_to_euro_str(stmt.gross_income_cents)
            ET.SubElement(institut, "EinbehalteneKapitalertragsteuer").text = _cents_to_euro_str(
                stmt.kapitalertragsteuer_withheld_cents
            )

    if rental_property_statements:
        vermietung = ET.SubElement(einkuenfte, "VermietungUndVerpachtung")
        for stmt in rental_property_statements:
            objekt = ET.SubElement(vermietung, "Objekt")
            ET.SubElement(objekt, "Adresse").text = stmt.property_address
            ET.SubElement(objekt, "Mieteinnahmen").text = _cents_to_euro_str(stmt.gross_rental_income_cents)
            ET.SubElement(objekt, "Werbungskosten").text = _cents_to_euro_str(
                stmt.deductible_expenses_cents
            )

    if self_employment_statements:
        selbstaendige_arbeit = ET.SubElement(einkuenfte, "SelbstaendigeArbeit")
        for stmt in self_employment_statements:
            betrieb = ET.SubElement(selbstaendige_arbeit, "Betrieb")
            ET.SubElement(betrieb, "Name").text = stmt.business_name
            ET.SubElement(betrieb, "Betriebseinnahmen").text = _cents_to_euro_str(stmt.gross_revenue_cents)
            ET.SubElement(betrieb, "Betriebsausgaben").text = _cents_to_euro_str(
                stmt.deductible_expenses_cents
            )

    if filing.number_of_children:
        kinder = ET.SubElement(steuerfall, "Kinderfreibetrag")
        ET.SubElement(kinder, "AnzahlKinder").text = str(filing.number_of_children)
        ET.SubElement(kinder, "Guenstigerpruefung").text = (
            "Kinderfreibetrag" if filing.kinderfreibetrag_applied else "Kindergeld"
        )
        if filing.kinderfreibetrag_applied:
            ET.SubElement(kinder, "KinderfreibetragBetrag").text = _cents_to_euro_str(
                filing.kinderfreibetrag_total_cents
            )
        else:
            ET.SubElement(kinder, "KindergeldErhalten").text = _cents_to_euro_str(
                filing.kindergeld_received_cents
            )

    berechnung = ET.SubElement(steuerfall, "Berechnung")
    ET.SubElement(berechnung, "ZuVersteuerndesEinkommen").text = _cents_to_euro_str(
        filing.taxable_income_cents
    )
    ET.SubElement(berechnung, "Einkommensteuer").text = _cents_to_euro_str(filing.income_tax_cents)
    ET.SubElement(berechnung, "Solidaritaetszuschlag").text = _cents_to_euro_str(
        filing.solidarity_surcharge_cents
    )
    ET.SubElement(berechnung, "Kirchensteuer").text = _cents_to_euro_str(filing.church_tax_cents)

    if capital_income_statements:
        ET.SubElement(berechnung, "AbgeltungsteuerKapitalertraege").text = _cents_to_euro_str(
            filing.capital_gains_tax_cents
        )
        ET.SubElement(berechnung, "SolidaritaetszuschlagKapitalertraege").text = _cents_to_euro_str(
            filing.capital_gains_soli_cents
        )
        ET.SubElement(berechnung, "KirchensteuerKapitalertraege").text = _cents_to_euro_str(
            filing.capital_gains_church_tax_cents
        )

    if rental_property_statements:
        ET.SubElement(berechnung, "EinkuenfteVermietungUndVerpachtung").text = _cents_to_euro_str(
            filing.net_rental_income_cents
        )

    if self_employment_statements:
        ET.SubElement(berechnung, "EinkuenfteSelbstaendigeArbeit").text = _cents_to_euro_str(
            filing.net_self_employment_income_cents
        )

    return ET.tostring(root, encoding="unicode", xml_declaration=False)
