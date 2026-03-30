"""PDF generation service for construction documents.

Generates professional PDF documents for:
  - RA Bills (Running Account Bills)
  - Payment Vouchers
  - Measurement Sheets
  - Labour Bills
"""

from __future__ import annotations

import io
from datetime import date
from decimal import Decimal

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

# ── Design constants ──────────────────────────────────────────────

ACCENT = colors.HexColor("#d97706")
ACCENT_LIGHT = colors.HexColor("#FFF9ED")
INK = colors.HexColor("#17231c")
MUTED = colors.HexColor("#536455")
LINE = colors.HexColor("#C4B8A0")
WHITE = colors.white

PAGE_MARGIN = 18 * mm


def _fmt_currency(value: float | Decimal | None) -> str:
    if value is None:
        return "—"
    return f"₹ {float(value):,.2f}"


def _fmt_date(d: date | None) -> str:
    if d is None:
        return "—"
    return d.strftime("%d %b %Y")


def _build_styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "PDFTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=INK,
            spaceAfter=2 * mm,
        ),
        "subtitle": ParagraphStyle(
            "PDFSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=MUTED,
            spaceAfter=4 * mm,
        ),
        "heading": ParagraphStyle(
            "PDFHeading",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=INK,
            spaceBefore=6 * mm,
            spaceAfter=2 * mm,
        ),
        "normal": ParagraphStyle(
            "PDFNormal",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            textColor=INK,
            leading=13,
        ),
        "bold": ParagraphStyle(
            "PDFBold",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=INK,
        ),
        "small": ParagraphStyle(
            "PDFSmall",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            textColor=MUTED,
        ),
    }


HEADER_STYLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
    ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, 0), 8),
    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
    ("FONTSIZE", (0, 1), (-1, -1), 8),
    ("TEXTCOLOR", (0, 1), (-1, -1), INK),
    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("GRID", (0, 0), (-1, -1), 0.4, LINE),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, ACCENT_LIGHT]),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
])

SUMMARY_STYLE = TableStyle([
    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("TEXTCOLOR", (0, 0), (-1, -1), INK),
    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ("LINEBELOW", (0, -1), (-1, -1), 1.2, ACCENT),
    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ("TOPPADDING", (0, 0), (-1, -1), 3),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
])


def _info_grid(rows: list[tuple[str, str]], col_widths: tuple = (45 * mm, 90 * mm)):
    """Creates a two-column label:value info grid."""
    data = [[Paragraph(f"<b>{label}</b>", _build_styles()["normal"]),
             Paragraph(value, _build_styles()["normal"])] for label, value in rows]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(PAGE_MARGIN, 12 * mm, "M2N Construction ERP — System Generated Document")
    canvas.drawRightString(A4[0] - PAGE_MARGIN, 12 * mm, f"Page {doc.page}")
    canvas.restoreState()


# ── RA Bill PDF ────────────────────────────────────────────────────


def generate_ra_bill_pdf(
    ra_bill: object,
    contract: object,
    project: object,
    vendor: object,
) -> bytes:
    """Generate an RA Bill PDF and return raw bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=PAGE_MARGIN,
        rightMargin=PAGE_MARGIN,
        topMargin=PAGE_MARGIN,
        bottomMargin=20 * mm,
    )
    styles = _build_styles()
    elements: list = []

    # Title
    elements.append(Paragraph("Running Account Bill", styles["title"]))
    elements.append(Paragraph(
        f"Bill #{ra_bill.bill_no} — {_fmt_date(ra_bill.bill_date)}",
        styles["subtitle"],
    ))

    # Info grid
    elements.append(_info_grid([
        ("Project", getattr(project, "name", "—")),
        ("Contract", f"{getattr(contract, 'contract_no', '—')} — {getattr(contract, 'title', '')}"),
        ("Vendor", getattr(vendor, "name", "—")),
        ("Period", f"{_fmt_date(ra_bill.period_from)} to {_fmt_date(ra_bill.period_to)}"),
        ("Status", (getattr(ra_bill, "status", "draft") or "draft").replace("_", " ").title()),
    ]))
    elements.append(Spacer(1, 4 * mm))

    # Line items table
    items = getattr(ra_bill, "items", []) or []
    if items:
        elements.append(Paragraph("Bill Items", styles["heading"]))
        header = ["#", "Description", "Unit", "Prev Qty", "Curr Qty", "Cum Qty", "Rate", "Amount"]
        rows = [header]
        for i, item in enumerate(items, 1):
            rows.append([
                str(i),
                str(getattr(item, "description_snapshot", "")),
                str(getattr(item, "unit_snapshot", "")),
                f"{float(getattr(item, 'prev_quantity', 0)):,.2f}",
                f"{float(getattr(item, 'curr_quantity', 0)):,.2f}",
                f"{float(getattr(item, 'cumulative_quantity', 0)):,.2f}",
                _fmt_currency(getattr(item, "rate", 0)),
                _fmt_currency(getattr(item, "amount", 0)),
            ])
        col_widths = [8 * mm, 52 * mm, 16 * mm, 20 * mm, 20 * mm, 20 * mm, 22 * mm, 22 * mm]
        t = Table(rows, colWidths=col_widths, repeatRows=1)
        t.setStyle(HEADER_STYLE)
        elements.append(t)

    # Deductions
    deductions = getattr(ra_bill, "deductions", []) or []
    if deductions:
        elements.append(Paragraph("Deductions", styles["heading"]))
        header = ["#", "Type", "Description", "% ", "Amount"]
        rows = [header]
        for i, d in enumerate(deductions, 1):
            pct = getattr(d, "percentage", None)
            rows.append([
                str(i),
                str(getattr(d, "deduction_type", "")),
                str(getattr(d, "description", "") or ""),
                f"{float(pct):.1f}%" if pct else "—",
                _fmt_currency(getattr(d, "amount", 0)),
            ])
        col_widths = [8 * mm, 35 * mm, 65 * mm, 20 * mm, 30 * mm]
        t = Table(rows, colWidths=col_widths, repeatRows=1)
        t.setStyle(HEADER_STYLE)
        elements.append(t)

    # Summary
    elements.append(Spacer(1, 4 * mm))
    summary_data = [
        ["Gross Amount", _fmt_currency(ra_bill.gross_amount)],
        ["Total Deductions", _fmt_currency(ra_bill.total_deductions)],
        ["Net Payable", _fmt_currency(ra_bill.net_payable)],
    ]
    t = Table(summary_data, colWidths=[50 * mm, 40 * mm], hAlign="RIGHT")
    t.setStyle(SUMMARY_STYLE)
    elements.append(t)

    doc.build(elements, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


# ── Payment Voucher PDF ────────────────────────────────────────────


def generate_payment_voucher_pdf(
    payment: object,
    contract: object,
    project: object,
    vendor: object,
) -> bytes:
    """Generate a Payment Voucher PDF."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=PAGE_MARGIN,
        rightMargin=PAGE_MARGIN,
        topMargin=PAGE_MARGIN,
        bottomMargin=20 * mm,
    )
    styles = _build_styles()
    elements: list = []

    elements.append(Paragraph("Payment Voucher", styles["title"]))
    elements.append(Paragraph(
        f"Payment #{payment.id} — {_fmt_date(payment.payment_date)}",
        styles["subtitle"],
    ))

    # Info grid
    mode = (getattr(payment, "payment_mode", None) or "").upper() or "—"
    elements.append(_info_grid([
        ("Project", getattr(project, "name", "—")),
        ("Contract", f"{getattr(contract, 'contract_no', '—')} — {getattr(contract, 'title', '')}"),
        ("Vendor / Payee", getattr(vendor, "name", "—")),
        ("Payment Mode", mode),
        ("Reference No.", getattr(payment, "reference_no", None) or "—"),
        ("Status", (getattr(payment, "status", "draft") or "draft").replace("_", " ").title()),
    ]))
    elements.append(Spacer(1, 4 * mm))

    # Allocation table
    allocations = getattr(payment, "allocations", []) or []
    if allocations:
        elements.append(Paragraph("Bill Allocations", styles["heading"]))
        header = ["#", "RA Bill #", "Allocated Amount"]
        rows = [header]
        for i, alloc in enumerate(allocations, 1):
            rows.append([
                str(i),
                f"Bill #{getattr(alloc, 'ra_bill_id', '—')}",
                _fmt_currency(getattr(alloc, "amount", 0)),
            ])
        t = Table(rows, colWidths=[10 * mm, 60 * mm, 40 * mm], repeatRows=1)
        t.setStyle(HEADER_STYLE)
        elements.append(t)

    # Summary
    elements.append(Spacer(1, 6 * mm))
    summary_data = [
        ["Payment Amount", _fmt_currency(payment.amount)],
    ]
    t = Table(summary_data, colWidths=[50 * mm, 40 * mm], hAlign="RIGHT")
    t.setStyle(SUMMARY_STYLE)
    elements.append(t)

    # Remarks
    remarks = getattr(payment, "remarks", None)
    if remarks:
        elements.append(Spacer(1, 4 * mm))
        elements.append(Paragraph("Remarks", styles["heading"]))
        elements.append(Paragraph(remarks, styles["normal"]))

    doc.build(elements, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


# ── Measurement Sheet PDF ──────────────────────────────────────────


def generate_measurement_sheet_pdf(
    measurement: object,
    contract: object,
    project: object,
) -> bytes:
    """Generate a Measurement Sheet PDF."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=PAGE_MARGIN,
        rightMargin=PAGE_MARGIN,
        topMargin=PAGE_MARGIN,
        bottomMargin=20 * mm,
    )
    styles = _build_styles()
    elements: list = []

    elements.append(Paragraph("Measurement Sheet", styles["title"]))
    elements.append(Paragraph(
        f"{measurement.measurement_no} — {_fmt_date(measurement.measurement_date)}",
        styles["subtitle"],
    ))

    elements.append(_info_grid([
        ("Project", getattr(project, "name", "—")),
        ("Contract", f"{getattr(contract, 'contract_no', '—')} — {getattr(contract, 'title', '')}"),
        ("Status", (getattr(measurement, "status", "draft") or "draft").replace("_", " ").title()),
    ]))
    elements.append(Spacer(1, 4 * mm))

    # Measurement items
    items = getattr(measurement, "items", []) or []
    if items:
        elements.append(Paragraph("Measurement Items", styles["heading"]))
        header = ["#", "BOQ Item", "Description", "Unit", "Quantity", "Remarks"]
        rows = [header]
        for i, item in enumerate(items, 1):
            rows.append([
                str(i),
                str(getattr(item, "item_code", getattr(item, "boq_item_code", "")) or ""),
                str(getattr(item, "description", "") or ""),
                str(getattr(item, "unit", "") or ""),
                f"{float(getattr(item, 'quantity', 0)):,.2f}",
                str(getattr(item, "remarks", "") or ""),
            ])
        col_widths = [8 * mm, 25 * mm, 55 * mm, 16 * mm, 22 * mm, 34 * mm]
        t = Table(rows, colWidths=col_widths, repeatRows=1)
        t.setStyle(HEADER_STYLE)
        elements.append(t)

    # Work done entries
    work_done = getattr(measurement, "work_done_entries", []) or []
    if work_done:
        elements.append(Paragraph("Work Done", styles["heading"]))
        header = ["#", "BOQ Item", "Description", "Quantity", "Rate", "Amount"]
        rows = [header]
        for i, wd in enumerate(work_done, 1):
            rows.append([
                str(i),
                str(getattr(wd, "boq_item_code", "") or ""),
                str(getattr(wd, "description", "") or ""),
                f"{float(getattr(wd, 'quantity', 0)):,.2f}",
                _fmt_currency(getattr(wd, "rate", 0)),
                _fmt_currency(getattr(wd, "amount", 0)),
            ])
        col_widths = [8 * mm, 25 * mm, 55 * mm, 22 * mm, 25 * mm, 25 * mm]
        t = Table(rows, colWidths=col_widths, repeatRows=1)
        t.setStyle(HEADER_STYLE)
        elements.append(t)

    # Remarks
    remarks = getattr(measurement, "remarks", None)
    if remarks:
        elements.append(Spacer(1, 4 * mm))
        elements.append(Paragraph("Remarks", styles["heading"]))
        elements.append(Paragraph(remarks, styles["normal"]))

    doc.build(elements, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


# ── Labour Bill PDF ────────────────────────────────────────────────


def generate_labour_bill_pdf(
    bill: object,
    contractor: object,
    project: object,
    contract: object | None = None,
) -> bytes:
    """Generate a Labour Bill PDF."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=PAGE_MARGIN,
        rightMargin=PAGE_MARGIN,
        topMargin=PAGE_MARGIN,
        bottomMargin=20 * mm,
    )
    styles = _build_styles()
    elements: list = []

    elements.append(Paragraph("Labour Bill", styles["title"]))
    elements.append(Paragraph(
        f"{bill.bill_no} — Period {_fmt_date(bill.period_start)} to {_fmt_date(bill.period_end)}",
        styles["subtitle"],
    ))

    info_rows = [
        ("Project", getattr(project, "name", "—")),
        ("Contractor", getattr(contractor, "contractor_name", "—")),
    ]
    if contract:
        info_rows.append(("Contract", f"{getattr(contract, 'contract_no', '—')} — {getattr(contract, 'title', '')}"))
    info_rows.extend([
        ("Status", (getattr(bill, "status", "draft") or "draft").replace("_", " ").title()),
    ])
    elements.append(_info_grid(info_rows))
    elements.append(Spacer(1, 4 * mm))

    # Bill items
    items = getattr(bill, "items", []) or []
    if items:
        elements.append(Paragraph("Labour Bill Items", styles["heading"]))
        header = ["#", "Labour", "Trade", "Days", "Rate", "Amount"]
        rows = [header]
        for i, item in enumerate(items, 1):
            rows.append([
                str(i),
                str(getattr(item, "labour_name", getattr(item, "full_name", "")) or ""),
                str(getattr(item, "trade", "") or ""),
                f"{float(getattr(item, 'days_worked', getattr(item, 'quantity', 0))):,.1f}",
                _fmt_currency(getattr(item, "daily_rate", getattr(item, "rate", 0))),
                _fmt_currency(getattr(item, "amount", 0)),
            ])
        col_widths = [8 * mm, 45 * mm, 30 * mm, 20 * mm, 28 * mm, 28 * mm]
        t = Table(rows, colWidths=col_widths, repeatRows=1)
        t.setStyle(HEADER_STYLE)
        elements.append(t)

    # Summary
    elements.append(Spacer(1, 4 * mm))
    summary_data = [
        ["Gross Amount", _fmt_currency(bill.gross_amount)],
        ["Deductions", _fmt_currency(bill.deductions)],
        ["Net Payable", _fmt_currency(bill.net_payable)],
    ]
    t = Table(summary_data, colWidths=[50 * mm, 40 * mm], hAlign="RIGHT")
    t.setStyle(SUMMARY_STYLE)
    elements.append(t)

    # Remarks
    remarks = getattr(bill, "remarks", None)
    if remarks:
        elements.append(Spacer(1, 4 * mm))
        elements.append(Paragraph("Remarks", styles["heading"]))
        elements.append(Paragraph(remarks, styles["normal"]))

    doc.build(elements, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
