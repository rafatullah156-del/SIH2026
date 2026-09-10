"""
Real PDF report generation using ReportLab.
Generates a proper Legal Metrology Compliance Report.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

# ── ReportLab imports ─────────────────────────────────────────────────────────
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import HRFlowable
import io

# ── Colours (Indian govt palette) ────────────────────────────────────────────
SAFFRON   = colors.HexColor("#FF6600")
NAVY      = colors.HexColor("#071C3D")
GREEN     = colors.HexColor("#046A38")
RED       = colors.HexColor("#DC2626")
ORANGE    = colors.HexColor("#D97706")
BLUE_LIGHT= colors.HexColor("#EEF4FF")
GREEN_LIGHT=colors.HexColor("#F0FDF4")
RED_LIGHT = colors.HexColor("#FEF2F2")
GREY_LIGHT= colors.HexColor("#F8F9FA")
GREY_TEXT = colors.HexColor("#6B7280")
BLACK     = colors.HexColor("#111827")
WHITE     = colors.white

# ── Score helpers ─────────────────────────────────────────────────────────────
def _score_color(score: float) -> colors.Color:
    if score >= 90: return GREEN
    if score >= 70: return ORANGE
    return RED

def _score_label(score: float) -> str:
    if score >= 90: return "COMPLIANT"
    if score >= 70: return "MINOR VIOLATIONS"
    if score >= 50: return "MAJOR VIOLATIONS"
    return "NON-COMPLIANT"

def _sev_color(sev: str) -> colors.Color:
    return {
        "high":   RED,
        "medium": ORANGE,
        "low":    GREY_TEXT,
    }.get(sev.lower(), GREY_TEXT)

def _sev_bg(sev: str) -> colors.Color:
    return {
        "high":   RED_LIGHT,
        "medium": colors.HexColor("#FFF7ED"),
        "low":    GREY_LIGHT,
    }.get(sev.lower(), GREY_LIGHT)

def _field_icon(value) -> str:
    return "✓" if value else "✗"

def _field_icon_color(value) -> colors.Color:
    return GREEN if value else RED

# ── Main PDF generator ────────────────────────────────────────────────────────
def generate_pdf(
    scan_id: str,
    fields: list[dict[str, Any]],
    violations: list[dict[str, Any]],
    score: float = 0.0,
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=15 * mm,
        title=f"LMPC Compliance Report - {scan_id[:8].upper()}",
        author="Legal Metrology Compliance Checker",
    )

    styles = getSampleStyleSheet()
    W = A4[0] - 30 * mm  # usable width

    # ── Custom paragraph styles ───────────────────────────────────────────────
    def S(name, **kw) -> ParagraphStyle:
        base = kw.pop("parent", "Normal")
        return ParagraphStyle(name, parent=styles[base], **kw)

    title_style   = S("Title2",   fontSize=16, textColor=WHITE,  alignment=TA_CENTER,
                       fontName="Helvetica-Bold", leading=20)
    sub_style     = S("Sub",      fontSize=9,  textColor=WHITE,  alignment=TA_CENTER,
                       fontName="Helvetica", leading=13)
    h2_style      = S("H2",       fontSize=11, textColor=NAVY,   fontName="Helvetica-Bold",
                       spaceBefore=6, spaceAfter=3)
    normal_style  = S("Norm",     fontSize=9,  textColor=BLACK,  leading=13)
    small_style   = S("Small",    fontSize=8,  textColor=GREY_TEXT, leading=11)
    bold_style    = S("Bold9",    fontSize=9,  textColor=BLACK,  fontName="Helvetica-Bold")
    center_style  = S("Center9",  fontSize=9,  textColor=BLACK,  alignment=TA_CENTER)
    right_style   = S("Right9",   fontSize=9,  textColor=BLACK,  alignment=TA_RIGHT)
    score_style   = S("Score",    fontSize=28, textColor=WHITE,  fontName="Helvetica-Bold",
                       alignment=TA_CENTER, leading=32)
    score_lbl     = S("ScoreLbl", fontSize=10, textColor=WHITE,  alignment=TA_CENTER,
                       fontName="Helvetica-Bold")
    mono_style    = S("Mono",     fontSize=8,  textColor=GREY_TEXT,
                       fontName="Courier", leading=11)

    story = []
    now = datetime.utcnow().strftime("%d %B %Y, %H:%M UTC")

    # ══════════════════════════════════════════════════════════════════════════
    # HEADER — tricolour bar + title
    # ══════════════════════════════════════════════════════════════════════════
    # Tricolour top bar
    tricolor = Table(
        [["", "", ""]],
        colWidths=[W / 3, W / 3, W / 3],
        rowHeights=[4],
    )
    tricolor.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), SAFFRON),
        ("BACKGROUND", (1, 0), (1, 0), WHITE),
        ("BACKGROUND", (2, 0), (2, 0), GREEN),
        ("LINEABOVE",  (0, 0), (-1, 0), 0, WHITE),
    ]))
    story.append(tricolor)

    # Navy header block
    header_data = [
        [Paragraph("LEGAL METROLOGY COMPLIANCE REPORT", title_style)],
        [Paragraph("Ministry of Consumer Affairs, Food &amp; Public Distribution", sub_style)],
        [Paragraph("Legal Metrology (Packaged Commodities) Rules, 2011", sub_style)],
    ]
    header_table = Table(header_data, colWidths=[W])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # META ROW — scan id, date, score box
    # ══════════════════════════════════════════════════════════════════════════
    high_count   = sum(1 for v in violations if v.get("severity") == "high")
    medium_count = sum(1 for v in violations if v.get("severity") == "medium")
    low_count    = sum(1 for v in violations if v.get("severity") == "low")
    total_v      = len(violations)
    sc           = round(score, 1)

    meta_left = Table([
        [Paragraph("<b>Scan Reference</b>", bold_style),
         Paragraph(scan_id[:8].upper(), normal_style)],
        [Paragraph("<b>Full Scan ID</b>", bold_style),
         Paragraph(f'<font name="Courier" size="7">{scan_id}</font>', normal_style)],
        [Paragraph("<b>Report Date</b>", bold_style),
         Paragraph(now, normal_style)],
        [Paragraph("<b>Total Violations</b>", bold_style),
         Paragraph(
             f'<font color="#DC2626">{high_count} High</font>  '
             f'<font color="#D97706">{medium_count} Medium</font>  '
             f'<font color="#6B7280">{low_count} Low</font>',
             normal_style,
         )],
    ], colWidths=[38 * mm, 70 * mm])
    meta_left.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GREY_LIGHT),
        ("GRID",       (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("FONTNAME",   (0, 0), (0, -1), "Helvetica-Bold"),
    ]))

    score_box = Table([
        [Paragraph(f"{sc}", score_style)],
        [Paragraph("/100", score_lbl)],
        [Paragraph(_score_label(sc), score_lbl)],
    ], colWidths=[40 * mm], rowHeights=[20 * mm, 6 * mm, 7 * mm])
    score_box.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), _score_color(sc)),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROUNDEDCORNERS", [4]),
    ]))

    meta_row = Table(
        [[meta_left, score_box]],
        colWidths=[W - 44 * mm, 44 * mm],
    )
    meta_row.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
        ("ALIGN",        (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(meta_row)
    story.append(Spacer(1, 5 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — EXTRACTED FIELDS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("1. EXTRACTED MANDATORY DECLARATIONS", h2_style))
    story.append(HRFlowable(width=W, thickness=1, color=NAVY, spaceAfter=3))

    FIELD_LABELS = {
        "common_name":    ("Common / Generic Name",         "Rule 6(1)(b)"),
        "mrp":            ("Retail Sale Price (MRP)",       "Rule 6(1)(e)"),
        "net_quantity":   ("Net Quantity",                  "Rule 6(1)(c)"),
        "mfd_date":       ("Month & Year of Mfg/Pkg",       "Rule 6(1)(d)"),
        "manufacturer":   ("Manufacturer / Packer Name & Address", "Rule 6(1)(a)"),
        "consumer_care":  ("Consumer Care Contact",         "Rule 6(1)(f)"),
        "best_before":    ("Best Before / Expiry",          "Rule 6(2)"),
        "fssai_license":  ("FSSAI Licence No.",             "FSS Act 2006"),
        "batch_no":       ("Batch / Lot Number",            "Rule 6"),
        "country_of_origin": ("Country of Origin",          "Rule 6(1)(a)"),
        "importer":       ("Importer Details",              "Rule 6(1)(a)"),
        "barcode":        ("Barcode (EAN)",                 "—"),
    }

    field_table_data = [[
        Paragraph("<b>Status</b>",      bold_style),
        Paragraph("<b>Field</b>",       bold_style),
        Paragraph("<b>Extracted Value</b>", bold_style),
        Paragraph("<b>Confidence</b>",  bold_style),
        Paragraph("<b>Rule Ref.</b>",   bold_style),
    ]]

    field_map = {f.get("field_name"): f for f in fields}
    shown_keys = list(FIELD_LABELS.keys())
    # also add any extra fields returned
    for f in fields:
        if f.get("field_name") not in shown_keys:
            shown_keys.append(f.get("field_name"))

    row_styles = []
    for row_i, key in enumerate(shown_keys, start=1):
        f = field_map.get(key)
        if not f:
            continue
        label, rule = FIELD_LABELS.get(key, (key.replace("_", " ").title(), "—"))
        value = f.get("field_value") or ""
        conf  = f.get("confidence") or 0.0
        has   = bool(value)
        icon  = "✓" if has else "✗"
        icon_col = GREEN if has else RED
        conf_pct = f"{conf * 100:.0f}%" if has else "—"
        value_display = (value[:80] + "…") if len(value) > 80 else value

        field_table_data.append([
            Paragraph(
                f'<font color="{"#046A38" if has else "#DC2626"}" size="12"><b>{icon}</b></font>',
                center_style,
            ),
            Paragraph(f"<b>{label}</b>", bold_style),
            Paragraph(value_display or "<i>Not detected</i>", normal_style),
            Paragraph(conf_pct, center_style),
            Paragraph(f'<font size="7" color="#6B7280">{rule}</font>', small_style),
        ])
        if not has:
            row_styles.append(("BACKGROUND", (0, row_i), (-1, row_i), RED_LIGHT))
        elif conf < 0.6:
            row_styles.append(("BACKGROUND", (0, row_i), (-1, row_i), colors.HexColor("#FFFBEB")))

    field_table = Table(
        field_table_data,
        colWidths=[12 * mm, 52 * mm, 72 * mm, 18 * mm, 22 * mm],
        repeatRows=1,
    )
    base_field_style = [
        ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, GREY_LIGHT]),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
        ("ALIGN",         (0, 0), (0, -1), "CENTER"),
        ("ALIGN",         (3, 0), (3, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
    ]
    field_table.setStyle(TableStyle(base_field_style + row_styles))
    story.append(field_table)
    story.append(Spacer(1, 5 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — VIOLATIONS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("2. COMPLIANCE VIOLATIONS", h2_style))
    story.append(HRFlowable(width=W, thickness=1, color=NAVY, spaceAfter=3))

    if not violations:
        ok_box = Table(
            [[Paragraph(
                '<font color="#046A38" size="12">✓</font>  '
                '<b>No violations found. Package is fully compliant.</b>',
                bold_style,
            )]],
            colWidths=[W],
        )
        ok_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), GREEN_LIGHT),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ]))
        story.append(ok_box)
    else:
        viol_table_data = [[
            Paragraph("<b>Sev.</b>",      bold_style),
            Paragraph("<b>Rule Code</b>", bold_style),
            Paragraph("<b>Field</b>",     bold_style),
            Paragraph("<b>Description</b>", bold_style),
            Paragraph("<b>Legal Ref.</b>",bold_style),
        ]]

        # Sort: high → medium → low
        sev_order = {"high": 0, "medium": 1, "low": 2}
        sorted_v = sorted(violations, key=lambda v: sev_order.get(v.get("severity", "low"), 3))

        viol_row_styles = []
        for vi, v in enumerate(sorted_v, start=1):
            sev    = v.get("severity", "low")
            code   = v.get("rule_code", "")
            field  = (v.get("field") or "").replace("_", " ").title()
            msg    = v.get("message", "")

            # Split message at | to get ref separately
            if " | Ref: " in msg:
                desc_part, ref_part = msg.split(" | Ref: ", 1)
                ref_part = ref_part.replace(", LM(PC) Rules, 2011", "").strip()
            else:
                desc_part = msg
                ref_part  = "—"

            desc_part = (desc_part[:120] + "…") if len(desc_part) > 120 else desc_part

            SEV_LABELS = {"high": "🔴 HIGH", "medium": "🟡 MED", "low": "⚪ LOW"}
            sev_label = SEV_LABELS.get(sev, sev.upper())

            viol_table_data.append([
                Paragraph(f"<b>{sev_label}</b>", bold_style),
                Paragraph(f'<font name="Courier" size="7">{code}</font>', mono_style),
                Paragraph(f"<b>{field}</b>", bold_style),
                Paragraph(desc_part, normal_style),
                Paragraph(f'<font size="7" color="#6B7280">{ref_part}</font>', small_style),
            ])
            viol_row_styles.append(
                ("BACKGROUND", (0, vi), (-1, vi), _sev_bg(sev))
            )

        viol_table = Table(
            viol_table_data,
            colWidths=[16 * mm, 32 * mm, 28 * mm, 72 * mm, 28 * mm],
            repeatRows=1,
        )
        viol_base_style = [
            ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0), 9),
            ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 5),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
            ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ]
        viol_table.setStyle(TableStyle(viol_base_style + viol_row_styles))
        story.append(viol_table)

    story.append(Spacer(1, 5 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — SUMMARY BOX
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("3. COMPLIANCE SUMMARY", h2_style))
    story.append(HRFlowable(width=W, thickness=1, color=NAVY, spaceAfter=3))

    fields_found  = sum(1 for f in fields if f.get("field_value"))
    fields_total  = len([k for k in FIELD_LABELS if k in field_map])

    summary_data = [
        ["Metric", "Value"],
        ["Compliance Score",      f"{sc} / 100"],
        ["Overall Status",        _score_label(sc)],
        ["Fields Detected",       f"{fields_found} / {fields_total}"],
        ["Total Violations",      str(total_v)],
        ["High Severity",         str(high_count)],
        ["Medium Severity",       str(medium_count)],
        ["Low / Review",          str(low_count)],
        ["Checked Against",       "LM(PC) Rules 2011, FSS Act 2006"],
    ]
    summary_table = Table(summary_data, colWidths=[60 * mm, W - 60 * mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, GREY_LIGHT]),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        # Highlight score row
        ("BACKGROUND",    (1, 1), (1, 1), _score_color(sc)),
        ("TEXTCOLOR",     (1, 1), (1, 1), WHITE),
        ("FONTNAME",      (1, 1), (1, 1), "Helvetica-Bold"),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 5 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4 — LEGAL NOTICE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("4. LEGAL NOTICE &amp; DISCLAIMER", h2_style))
    story.append(HRFlowable(width=W, thickness=1, color=NAVY, spaceAfter=3))

    notice_text = """
This report has been generated automatically by the <b>Legal Metrology Compliance Checker</b>
(SIH26034) using Optical Character Recognition (OCR) and rule-based analysis against the
<b>Legal Metrology (Packaged Commodities) Rules, 2011</b> under the Legal Metrology Act, 2009.

<br/><br/>
<b>Important:</b> This report is intended as an <b>assistive tool</b> for enforcement officers 
of the Legal Metrology Department. All findings must be verified against the physical 
product before initiating any enforcement action. OCR accuracy depends on image quality; 
low-confidence fields are marked for manual review.

<br/><br/>
Fields marked as <font color="#DC2626"><b>NOT DETECTED</b></font> may be present on the 
physical label but not visible in the submitted image due to lighting, angle, or obstruction.
Retake with better lighting if required.

<br/><br/>
Enforcement action under <b>Section 33, 36, and 48 of the Legal Metrology Act, 2009</b> 
may be initiated based on confirmed violations found upon physical inspection.
    """
    story.append(Paragraph(notice_text, small_style))
    story.append(Spacer(1, 5 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # FOOTER
    # ══════════════════════════════════════════════════════════════════════════
    story.append(HRFlowable(width=W, thickness=0.5, color=GREY_TEXT, spaceBefore=2))
    footer_data = [[
        Paragraph(
            f'<font size="7" color="#6B7280">Scan ID: {scan_id} | '
            f'Generated: {now} | SIH26034 Legal Metrology Compliance Checker</font>',
            small_style,
        ),
        Paragraph(
            '<font size="7" color="#6B7280">Ministry of Consumer Affairs, '
            'Food &amp; Public Distribution, Govt. of India</font>',
            ParagraphStyle("FR", parent=small_style, alignment=TA_RIGHT),
        ),
    ]]
    footer_table = Table(footer_data, colWidths=[W / 2, W / 2])
    footer_table.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]))
    story.append(footer_table)

    # ── Build PDF ─────────────────────────────────────────────────────────────
    doc.build(story)
    return buf.getvalue()


# ── JSON report (unchanged but improved) ─────────────────────────────────────
def generate_json_report(
    scan_id: str,
    fields: list[dict[str, Any]],
    violations: list[dict[str, Any]],
    score: float,
) -> bytes:
    high   = sum(1 for v in violations if v.get("severity") == "high")
    medium = sum(1 for v in violations if v.get("severity") == "medium")
    low    = sum(1 for v in violations if v.get("severity") == "low")

    report = {
        "scanId":    scan_id,
        "score":     round(score, 2),
        "status":    (
            "compliant"         if score >= 90 else
            "minor_violations"  if score >= 70 else
            "major_violations"  if score >= 50 else
            "non_compliant"
        ),
        "generatedAt": datetime.utcnow().isoformat() + "Z",
        "summary": {
            "totalViolations":  len(violations),
            "highSeverity":     high,
            "mediumSeverity":   medium,
            "lowSeverity":      low,
            "fieldsExtracted":  sum(1 for f in fields if f.get("field_value")),
            "fieldsTotal":      len(fields),
            "legalReference":   "Legal Metrology (Packaged Commodities) Rules, 2011",
        },
        "fields":     fields,
        "violations": violations,
    }
    return json.dumps(report, indent=2, default=str).encode("utf-8")