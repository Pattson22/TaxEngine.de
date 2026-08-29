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

from app.models.tax_filing import TaxFiling
from app.models.user import User
from app.models.wage_tax_certificate import WageTaxCertificate

_ELSTER_NAMESPACE = "http://www.elster.de/2002/XMLSchema"


def _cents_to_euro_str(cents: int | None) -> str:
    """ERiC's numeric fields are plain decimal strings, not cents."""
    if cents is None:
        cents = 0
    euros, remainder = divmod(cents, 100)
    return f"{euros}.{remainder:02d}"


def build_est_xml(user: User, filing: TaxFiling, wage_certs: list[WageTaxCertificate]) -> str:
    """Serialize one user/filing/wage-certificates into the (illustrative)
    XML payload for an ESt submission.

    Args:
        user: the taxpayer -- must have `tax_identification_number` set
            (ERiC requires the Steuer-ID; a real submission_service caller
            should validate this before calling here, this function does
            not re-validate it).
        filing: the CALCULATED/FEE_PAID filing being submitted.
        wage_certs: this filing's wage_tax_certificates rows.

    Returns:
        A UTF-8 XML string, NOT yet validated against the real ERiC schema
        (that happens in EricClient.validate_xml).
    """
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

    berechnung = ET.SubElement(steuerfall, "Berechnung")
    ET.SubElement(berechnung, "ZuVersteuerndesEinkommen").text = _cents_to_euro_str(
        filing.taxable_income_cents
    )
    ET.SubElement(berechnung, "Einkommensteuer").text = _cents_to_euro_str(filing.income_tax_cents)
    ET.SubElement(berechnung, "Solidaritaetszuschlag").text = _cents_to_euro_str(
        filing.solidarity_surcharge_cents
    )
    ET.SubElement(berechnung, "Kirchensteuer").text = _cents_to_euro_str(filing.church_tax_cents)

    return ET.tostring(root, encoding="unicode", xml_declaration=False)
