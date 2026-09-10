"""
Clean, officer-friendly PDF report.
Simple 3-section layout: Score → Declarations → Violations.
Fixed: ReportLab color hex format (#DC2626 not dc2626)
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any
import io

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

# ── Palette ──────────────────────────────────────────────────────────────────
SAFFRON  = colors.HexColor("#FF6600")
NAVY     = colors.HexColor("#0A2A5E")
GREEN    = colors.HexColor("#15803D")
GREEN_BG = colors.HexColor("#DCFCE7")
RED      = colors.HexColor("#DC2626")
RED_BG   = colors.HexColor("#FEE2E2")
AMBER    = colors.HexColor("#D97706")
AMBER_BG = colors.HexColor("#FEF3C7")
GREY_BG  = colors.HexColor("#F3F4F6")
GREY_BDR = colors.HexColor("#D1D5DB")
GREY_TXT = colors.HexColor("#6B7280")
BLACK    = colors.HexColor("#111827")
WHITE    = colors.white

# ── Hex strings for ReportLab XML/markup (must include #) ────────────────────
_SEV_HEX = {
    "high":   "#DC2626",
    "medium": "#D97706",
    "low":    "#6B7280",
}
_SEV_BG = {
    "high":   RED_BG,
    "medium": AMBER_BG,
    "low":    GREY_BG,
}
_SEV_LABEL = {
    "high":   "HIGH",
    "medium": "MEDIUM",
    "low":    "LOW",
}


def _score_color(s: float):
    if s >= 90: return GREEN
    if s >= 70: return AMBER
    return RED


def _score_label(s: float) -> str:
    if s >= 90: return "COMPLIANT"
    if s >= 70: return "MINOR VIOLATIONS"
    if s >= 50: return "MAJOR VIOLATIONS"
    return "NON-COMPLIANT"


# ── Field order ───────────────────────────────────────────────────────────────
MANDATORY_FIELDS = [
    ("common_name",   "Product / Common Name",          "Rule 6(1)(b)"),
    ("mrp",           "MRP (Incl. of all taxes)",       "Rule 6(1)(e)"),
    ("net_quantity",  "Net Quantity",                   "Rule 6(1)(c)"),
    ("mfd_date",      "Month & Year of Manufacture",    "Rule 6(1)(d)"),
    ("manufacturer",  "Manufacturer Name & Address",    "Rule 6(1)(a)"),
    ("consumer_care", "Consumer Care Contact",          "Rule 6(1)(f)"),
]
OPTIONAL_FIELDS = [
    ("best_before",      "Best Before / Expiry",        "Rule 6(2)"),
    ("fssai_license",    "FSSAI Licence Number",        "FSS Act 2006"),
    ("batch_no",         "Batch / Lot Number",          "—"),
    ("country_of_origin","Country of Origin",           "Rule 6(1)(a)"),
    ("importer",         "Importer Details",            "Rule 6(1)(a)"),
]


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
        title=f"LMPC Report {scan_id[:8].upper()}",
    )
    styles = getSampleStyleSheet()
    W = A4[0] - 30 * mm  # usable width

    def S(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    # Styles
    title_st  = S("t",  fontSize=17, textColor=WHITE,    fontName="Helvetica-Bold",
                  alignment=TA_CENTER, leading=22)
    sub_st    = S("s",  fontSize=9,  textColor=WHITE,    alignment=TA_CENTER, leading=13)
    h2_st     = S("h2", fontSize=12, textColor=NAVY,     fontName="Helvetica-Bold",
                  spaceBefore=4, spaceAfter=4)
    body_st   = S("b",  fontSize=10, textColor=BLACK,    leading=14)
    small_st  = S("sm", fontSize=8,  textColor=GREY_TXT, leading=11)
    bold_st   = S("bo", fontSize=10, textColor=BLACK,    fontName="Helvetica-Bold")
    cell_st   = S("c",  fontSize=9,  textColor=BLACK,    leading=13)
    mono_st   = S("mo", fontSize=7,  textColor=GREY_TXT, fontName="Courier")
    score_st  = S("sc", fontSize=42, textColor=WHITE,    fontName="Helvetica-Bold",
                  alignment=TA_CENTER, leading=46)
    score_lb  = S("sl", fontSize=11, textColor=WHITE,    fontName="Helvetica-Bold",
                  alignment=TA_CENTER, leading=14)
    right_st  = S("r",  fontSize=7,  textColor=GREY_TXT, alignment=TA_RIGHT, leading=11)

    story = []
    now = datetime.utcnow().strftime("%d %b %Y, %H:%M UTC")
    sc  = round(score, 1)

    high   = sum(1 for v in violations if v.get("severity") == "high")
    medium = sum(1 for v in violations if v.get("severity") == "medium")
    low    = sum(1 for v in violations if v.get("severity") == "low")

    # ══════════════════════════════════════════════════════════════════════════
    # HEADER
    # ══════════════════════════════════════════════════════════════════════════
    tri = Table([["", "", ""]], colWidths=[W / 3] * 3, rowHeights=[5])
    tri.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), SAFFRON),
        ("BACKGROUND", (1, 0), (1, 0), WHITE),
        ("BACKGROUND", (2, 0), (2, 0), GREEN),
    ]))
    story.append(tri)

    hdr = Table([
        [Paragraph("LEGAL METROLOGY COMPLIANCE REPORT", title_st)],
        [Paragraph("Ministry of Consumer Affairs, Food &amp; Public Distribution", sub_st)],
        [Paragraph("Legal Metrology (Packaged Commodities) Rules, 2011", sub_st)],
    ], colWidths=[W])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 6 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # SCORE CARD
    # ══════════════════════════════════════════════════════════════════════════
    left_info = Table([
        [Paragraph("<b>Scan Reference</b>", bold_st),
         Paragraph(scan_id[:8].upper(), cell_st)],
        [Paragraph("<b>Report Date</b>", bold_st),
         Paragraph(now, cell_st)],
        [Paragraph("<b>Total Issues</b>", bold_st),
         Paragraph(str(len(violations)), cell_st)],
        [Paragraph("<b>Severity</b>", bold_st),
         Paragraph(
             f'<font color="#DC2626"><b>{high} High</b></font>   '
             f'<font color="#D97706"><b>{medium} Medium</b></font>   '
             f'<font color="#6B7280"><b>{low} Low</b></font>',
             cell_st,
         )],
    ], colWidths=[45 * mm, 88 * mm])
    left_info.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), GREY_BG),
        ("GRID",          (0, 0), (-1, -1), 0.4, GREY_BDR),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
    ]))

    score_box = Table([
        [Paragraph(f"{sc}", score_st)],
        [Paragraph("out of 100", score_lb)],
        [Paragraph(_score_label(sc), score_lb)],
    ], colWidths=[62 * mm], rowHeights=[30 * mm, 7 * mm, 9 * mm])
    score_box.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), _score_color(sc)),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    score_row = Table([[left_info, score_box]], colWidths=[W - 64 * mm, 64 * mm])
    score_row.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(score_row)
    story.append(Spacer(1, 7 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1: MANDATORY DECLARATIONS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("1.  MANDATORY DECLARATIONS (Rule 6)", h2_st))
    story.append(HRFlowable(width=W, thickness=1.2, color=NAVY, spaceAfter=4))

    field_map = {f.get("field_name"): f for f in fields}

    tbl_hdr = [
        Paragraph("<b>Status</b>", bold_st),
        Paragraph("<b>Declaration</b>", bold_st),
        Paragraph("<b>Value Extracted</b>", bold_st),
        Paragraph("<b>Rule</b>", bold_st),
    ]
    rows = [tbl_hdr]
    row_styles = []

    def add_field_row(key, label, rule, row_index):
        f = field_map.get(key)
        value = (f or {}).get("field_value") or ""
        has = bool(value)
        icon = "YES" if has else "NO"
        icon_color = "#15803D" if has else "#DC2626"
        bg = GREEN_BG if has else RED_BG
        val_display = value if value else "NOT DETECTED"
        if len(val_display) > 90:
            val_display = val_display[:90] + "..."
        rows.append([
            Paragraph(
                f'<font color="{icon_color}"><b>{icon}</b></font>',
                S(f"ic{row_index}", fontSize=9, alignment=TA_CENTER,
                  fontName="Helvetica-Bold"),
            ),
            Paragraph(f"<b>{label}</b>", cell_st),
            Paragraph(val_display, cell_st),
            Paragraph(f'<font size="7" color="#6B7280">{rule}</font>', small_st),
        ])
        row_styles.append(("BACKGROUND", (0, row_index), (-1, row_index), bg))

    for i, (k, label, rule) in enumerate(MANDATORY_FIELDS, start=1):
        add_field_row(k, label, rule, i)

    # Optional fields that were detected
    opt_start = len(MANDATORY_FIELDS) + 1
    opt_count = 0
    for k, label, rule in OPTIONAL_FIELDS:
        if k in field_map and field_map[k].get("field_value"):
            add_field_row(k, label, rule, opt_start + opt_count)
            opt_count += 1

    field_tbl = Table(
        rows,
        colWidths=[16 * mm, 58 * mm, 82 * mm, 24 * mm],
        repeatRows=1,
    )
    field_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 10),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, GREY_BG]),
        ("GRID",          (0, 0), (-1, -1), 0.4, GREY_BDR),
        ("ALIGN",         (0, 0), (0, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("FONTSIZE",      (0, 1), (-1, -1), 9),
    ] + row_styles))
    story.append(field_tbl)
    story.append(Spacer(1, 7 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2: VIOLATIONS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("2.  VIOLATIONS FOUND", h2_st))
    story.append(HRFlowable(width=W, thickness=1.2, color=NAVY, spaceAfter=4))

    if not violations:
        ok_tbl = Table([[
            Paragraph(
                '<font color="#15803D" size="13"><b>'
                'NO VIOLATIONS FOUND — Package is fully compliant.'
                '</b></font>',
                S("ok", fontSize=12, textColor=GREEN, alignment=TA_CENTER),
            )
        ]], colWidths=[W])
        ok_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), GREEN_BG),
            ("TOPPADDING",    (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ("BOX",           (0, 0), (-1, -1), 1, GREEN),
        ]))
        story.append(ok_tbl)
    else:
        sev_order = {"high": 0, "medium": 1, "low": 2}
        sorted_v = sorted(
            violations,
            key=lambda v: sev_order.get(v.get("severity", "low"), 3),
        )

        for idx, v in enumerate(sorted_v, start=1):
            sev  = v.get("severity", "low")
            code = v.get("rule_code", "")
            msg  = v.get("message", "")

            if " | Ref: " in msg:
                desc, ref = msg.split(" | Ref: ", 1)
                ref = ref.replace(", LM(PC) Rules, 2011", "").strip()
            else:
                desc, ref = msg, "—"

            # Use plain hex strings — NO .hexval() call
            col_hex = _SEV_HEX.get(sev, "#6B7280")
            bg_col  = _SEV_BG.get(sev, GREY_BG)
            lbl     = _SEV_LABEL.get(sev, sev.upper())

            # Number badge
            badge = Table([[
                Paragraph(
                    f'<font color="white"><b>{idx}</b></font>',
                    S(f"bd{idx}", fontSize=13, textColor=WHITE,
                      alignment=TA_CENTER, fontName="Helvetica-Bold"),
                )
            ]], colWidths=[10 * mm], rowHeights=[10 * mm])
            badge.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
                ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
            ]))

            # Info block
            info = Table([
                [
                    Paragraph(
                        f'<font color="{col_hex}"><b>&#9679;  {lbl} SEVERITY</b></font>',
                        bold_st,
                    ),
                    Paragraph(
                        f'<font name="Courier" size="7" color="#6B7280">{code}</font>',
                        mono_st,
                    ),
                ],
                [Paragraph(desc, body_st), ""],
                [Paragraph(f"<i>Legal Reference: {ref}</i>", small_st), ""],
            ], colWidths=[W - 36 * mm, 28 * mm])
            info.setStyle(TableStyle([
                ("SPAN",          (0, 1), (1, 1)),
                ("SPAN",          (0, 2), (1, 2)),
                ("BACKGROUND",    (0, 0), (-1, -1), bg_col),
                ("LEFTPADDING",   (0, 0), (-1, -1), 10),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
                ("TOPPADDING",    (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("ALIGN",         (1, 0), (1, 0), "RIGHT"),
                ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ]))

            row_tbl = Table([[badge, info]], colWidths=[12 * mm, W - 12 * mm])
            row_tbl.setStyle(TableStyle([
                ("VALIGN",        (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING",   (0, 0), (-1, -1), 0),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
                ("TOPPADDING",    (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(row_tbl)
            story.append(Spacer(1, 3 * mm))

    story.append(Spacer(1, 5 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3: RECOMMENDED ACTION (only if violations)
    # ══════════════════════════════════════════════════════════════════════════
    if violations:
        action = Table([[
            Paragraph(
                f"<b>RECOMMENDED ACTION:</b>  Issue show-cause notice under "
                f"Section 33 of the Legal Metrology Act, 2009. "
                f"Verify all <b>{len(violations)} violations</b> against the physical package "
                f"before initiating enforcement. "
                f"Priority: <b>{high} high-severity</b> violation(s) require immediate action.",
                S("act", fontSize=10, textColor=BLACK, leading=15),
            )
        ]], colWidths=[W])
        action.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), AMBER_BG),
            ("BOX",           (0, 0), (-1, -1), 1.2, AMBER),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ]))
        story.append(action)
        story.append(Spacer(1, 5 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4: SUMMARY TABLE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("3.  COMPLIANCE SUMMARY", h2_st))
    story.append(HRFlowable(width=W, thickness=1.2, color=NAVY, spaceAfter=4))

    fields_found = sum(1 for f in fields if f.get("field_value"))

    summary_data = [
        ["Metric", "Value"],
        ["Compliance Score",    f"{sc} / 100"],
        ["Overall Status",      _score_label(sc)],
        ["Fields Detected",     f"{fields_found} of {len(fields)}"],
        ["High Severity",       str(high)],
        ["Medium Severity",     str(medium)],
        ["Low / Review",        str(low)],
        ["Total Violations",    str(len(violations))],
        ["Checked Against",     "LM(PC) Rules 2011 + FSS Act 2006"],
    ]
    sum_tbl = Table(summary_data, colWidths=[70 * mm, W - 70 * mm])
    sum_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME",      (0, 1), (0, -1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, GREY_BG]),
        ("GRID",          (0, 0), (-1, -1), 0.4, GREY_BDR),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        # Highlight score row
        ("BACKGROUND",    (1, 1), (1, 1), _score_color(sc)),
        ("TEXTCOLOR",     (1, 1), (1, 1), WHITE),
        ("FONTNAME",      (1, 1), (1, 1), "Helvetica-Bold"),
    ]))
    story.append(sum_tbl)
    story.append(Spacer(1, 5 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # FOOTER
    # ══════════════════════════════════════════════════════════════════════════
    story.append(HRFlowable(width=W, thickness=0.5, color=GREY_BDR, spaceBefore=2))
    footer = Table([[
        Paragraph(
            f'<font size="7" color="#6B7280">'
            f'Scan ID: {scan_id[:8].upper()} · {now} · '
            f'SIH26034 Legal Metrology Compliance Checker</font>',
            small_st,
        ),
        Paragraph(
            '<font size="7" color="#6B7280">'
            'Ministry of Consumer Affairs,<br/>'
            'Food &amp; Public Distribution, Govt. of India</font>',
            right_st,
        ),
    ]], colWidths=[W / 2, W / 2])
    footer.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]))
    story.append(footer)

    doc.build(story)
    return buf.getvalue()


# ── JSON report ───────────────────────────────────────────────────────────────
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
        "scanId":      scan_id,
        "score":       round(score, 2),
        "status": (
            "compliant"        if score >= 90 else
            "minor_violations" if score >= 70 else
            "major_violations" if score >= 50 else
            "non_compliant"
        ),
        "generatedAt": datetime.utcnow().isoformat() + "Z",
        "summary": {
            "totalViolations": len(violations),
            "highSeverity":    high,
            "mediumSeverity":  medium,
            "lowSeverity":     low,
            "fieldsExtracted": sum(1 for f in fields if f.get("field_value")),
            "fieldsTotal":     len(fields),
            "legalReference":  "Legal Metrology (Packaged Commodities) Rules, 2011",
        },
        "fields":     fields,
        "violations": violations,
    }
    return json.dumps(report, indent=2, default=str).encode("utf-8")