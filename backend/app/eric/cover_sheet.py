"""
Builds the printable cover sheet for a KOMPRIMIERT (unauthenticated)
ELSTER submission.

*** NOT THE OFFICIAL BZST BARCODE FORM ***
The real "komprimierte Steuererklärung" printout that certified tax
software produces carries a machine-readable barcode/reference generated
by ERiC itself at transmission time, which only exists once a real
NativeEricClient (see app/eric/client.py) actually calls EricBearbeiteVorgang.
This is a functional stand-in: a human-readable summary the taxpayer signs
and mails, referencing the same Transferticket their electronic submission
already produced (from StubEricClient today, from ERiC once it's real) so
the paper and the electronic record can be matched up manually. Treat it
as an MVP substitute, not a drop-in replacement for the barcode form.
"""

from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.tax_filing import TaxFiling
from app.models.user import User


def _format_euros(cents: int | None) -> str:
    """German thousand/decimal convention: 1.234,56 €. Unlike xml_builder's
    `_cents_to_euro_str`, this is for human display, not ERiC's wire
    format, so it isn't the same helper."""
    if cents is None:
        cents = 0
    sign = "-" if cents < 0 else ""
    euros, remainder = divmod(abs(cents), 100)
    grouped = f"{euros:,}".replace(",", ".")
    return f"{sign}{grouped},{remainder:02d} €"


def build_cover_sheet_pdf(user: User, filing: TaxFiling) -> bytes:
    """Render the cover sheet for `filing` as a PDF, returned as bytes.

    Callers must ensure `filing` is ACCEPTED (or at least SUBMITTED) and
    `filing.submission_mode is SubmissionMode.KOMPRIMIERT` before calling
    this -- it does not re-validate either, matching xml_builder's
    "pure function, caller validates" convention.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=22 * mm,
        bottomMargin=22 * mm,
        leftMargin=22 * mm,
        rightMargin=22 * mm,
        title=f"Komprimierte Einkommensteuererklaerung {filing.tax_year}",
        # Uncompressed: this is a one-page document, the size difference is
        # negligible, and it keeps the output greppable in tests/debugging.
        pageCompression=0,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CoverTitle", parent=styles["Title"], fontSize=16, spaceAfter=2 * mm
    )
    label_style = ParagraphStyle(
        "Label", parent=styles["Normal"], textColor=colors.HexColor("#5b5648"), fontSize=8
    )
    body_style = styles["Normal"]
    small_style = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, leading=11)

    story: list = []

    story.append(Paragraph("Komprimierte Einkommensteuererklärung", title_style))
    story.append(Paragraph(f"Veranlagungsjahr {filing.tax_year}", body_style))
    story.append(Spacer(1, 6 * mm))

    address_lines = [f"{user.first_name} {user.last_name}"]
    if user.street:
        address_lines.append(f"{user.street} {user.house_number or ''}".strip())
    if user.postal_code or user.city:
        address_lines.append(f"{user.postal_code or ''} {user.city or ''}".strip())

    identity_rows = [
        ["Steuerpflichtiger", "<br/>".join(address_lines)],
        ["Steuer-ID", user.tax_identification_number or "—"],
        ["Steuernummer", user.steuernummer or "—"],
        ["Transferticket", filing.elster_transfer_ticket or "—"],
    ]
    identity_table = Table(
        [[Paragraph(f"<b>{label}</b>", label_style), Paragraph(value, body_style)] for label, value in identity_rows],
        colWidths=[45 * mm, None],
    )
    identity_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
            ]
        )
    )
    story.append(identity_table)
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("Ergebnis der Berechnung", styles["Heading3"]))
    figure_rows = [
        ("Zu versteuerndes Einkommen", filing.taxable_income_cents),
        ("Einkommensteuer", filing.income_tax_cents),
        ("Solidaritätszuschlag", filing.solidarity_surcharge_cents),
        ("Kirchensteuer", filing.church_tax_cents),
    ]
    if filing.capital_gains_tax_cents:
        figure_rows.append(("Abgeltungsteuer auf Kapitalerträge", filing.capital_gains_tax_cents))
    figure_rows.append(("Erstattung/Nachzahlung", filing.estimated_refund_cents))

    figures_table = Table(
        [[label, _format_euros(cents)] for label, cents in figure_rows],
        colWidths=[110 * mm, None],
    )
    figures_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor("#d8d3c4")),
                ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.HexColor("#1c1b18")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
            ]
        )
    )
    story.append(figures_table)
    story.append(Spacer(1, 10 * mm))

    story.append(
        Paragraph(
            "Ich versichere, dass ich die Angaben in der elektronisch übermittelten "
            "Steuererklärung wahrheitsgemäß nach bestem Wissen und Gewissen gemacht habe.",
            body_style,
        )
    )
    story.append(Spacer(1, 14 * mm))
    signature_table = Table(
        [["_" * 40, "_" * 40]],
        colWidths=[75 * mm, 75 * mm],
    )
    story.append(signature_table)
    story.append(
        Table(
            [["Ort, Datum", "Unterschrift"]],
            colWidths=[75 * mm, 75 * mm],
            style=TableStyle([("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#5b5648"))]),
        )
    )
    story.append(Spacer(1, 10 * mm))
    story.append(
        Paragraph(
            "Bitte ausdrucken, unterschreiben und an das für Sie zuständige Finanzamt "
            "senden (siehe Ihre Steuernummer bzw. Ihren letzten Steuerbescheid). Diese "
            "Übersicht wird von TaxEngine.de erstellt und ist kein amtliches Formular.",
            small_style,
        )
    )

    doc.build(story)
    return buffer.getvalue()
