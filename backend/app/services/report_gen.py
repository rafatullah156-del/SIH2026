"""
Clean, officer-friendly PDF report.
Simple 3-section layout: Score → Declarations → Violations.
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

# ── Palette ─────────────────────────────────────────────────────────────────
SAFFRON   = colors.HexColor("#FF6600")
NAVY      = colors.HexColor("#0A2A5E")
GREEN     = colors.HexColor("#15803D")
GREEN_BG  = colors.HexColor("#DCFCE7")
RED       = colors.HexColor("#DC2626")
RED_BG    = colors.HexColor("#FEE2E2")
AMBER     = colors.HexColor("#D97706")
AMBER_BG  = colors.HexColor("#FEF3C7")
GREY_BG   = colors.HexColor("#F3F4F6")
GREY_BDR  = colors.HexColor("#D1D5DB")
GREY_TXT  = colors.HexColor("#6B7280")
BLACK     = colors.HexColor("#111827")
WHITE     = colors.white


def _score_color(s: float):
    if s >= 90: return GREEN
    if s >= 70: return AMBER
    return RED


def _score_label(s: float) -> str:
    if s >= 90: return "COMPLIANT"
    if s >= 70: return "MINOR VIOLATIONS"
    if s >= 50: return "MAJOR VIOLATIONS"
    return "NON-COMPLIANT"


# ── Field label map (order matters — mandatory first) ───────────────────────
FIELD_ORDER = [
    ("common_name",      "Product Name",               "R6(1)(b)"),
    ("mrp",              "MRP (Incl. all taxes)",      "R6(1)(e)"),
    ("net_quantity",     "Net Quantity",               "R6(1)(c)"),
    ("mfd_date",         "Month & Year of Mfg",        "R6(1)(d)"),
    ("manufacturer",     "Manufacturer Name + Address","R6(1)(a)"),
    ("consumer_care",    "Consumer Care Contact",      "R6(1)(f)"),
]
OPTIONAL_ORDER = [
    ("best_before",      "Best Before / Expiry",       "R6(2)"),
    ("fssai_license",    "FSSAI Licence Number",       "FSS Act"),
    ("batch_no",         "Batch / Lot Number",         "—"),
    ("country_of_origin","Country of Origin",          "R6(1)(a)"),
    ("importer",         "Importer Details",           "R6(1)(a)"),
]


def generate_pdf(
    scan_id: str,
    fields: list[dict[str, Any]],
    violations: list[dict[str, Any]],
    score: float = 0.0,
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=12*mm, bottomMargin=15*mm,
        title=f"LMPC Report {scan_id[:8]}",
    )
    styles = getSampleStyleSheet()
    W = A4[0] - 30*mm

    def S(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    title_st   = S("t",  fontSize=17, textColor=WHITE,  fontName="Helvetica-Bold", alignment=TA_CENTER, leading=20)
    sub_st     = S("s",  fontSize=9,  textColor=WHITE,  alignment=TA_CENTER, leading=13)
    h2_st      = S("h2", fontSize=12, textColor=NAVY,   fontName="Helvetica-Bold", spaceBefore=4, spaceAfter=4)
    body_st    = S("b",  fontSize=10, textColor=BLACK,  leading=14)
    small_st   = S("sm", fontSize=8,  textColor=GREY_TXT, leading=11)
    bold_st    = S("bo", fontSize=10, textColor=BLACK,  fontName="Helvetica-Bold")
    cell_st    = S("c",  fontSize=9,  textColor=BLACK,  leading=12)
    mono_st    = S("m",  fontSize=7,  textColor=GREY_TXT, fontName="Courier")
    score_st   = S("sc", fontSize=42, textColor=WHITE,  fontName="Helvetica-Bold", alignment=TA_CENTER, leading=46)
    score_lb   = S("sl", fontSize=11, textColor=WHITE,  fontName="Helvetica-Bold", alignment=TA_CENTER, leading=13)

    story = []
    now = datetime.utcnow().strftime("%d %b %Y, %H:%M UTC")

    high   = sum(1 for v in violations if v.get("severity") == "high")
    medium = sum(1 for v in violations if v.get("severity") == "medium")
    low    = sum(1 for v in violations if v.get("severity") == "low")
    sc     = round(score, 1)

    # ═══════════════════════════════════════════════════════════════════════
    # 1. HEADER
    # ═══════════════════════════════════════════════════════════════════════
    tri = Table([["", "", ""]], colWidths=[W/3]*3, rowHeights=[5])
    tri.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,0), SAFFRON),
        ("BACKGROUND", (1,0), (1,0), WHITE),
        ("BACKGROUND", (2,0), (2,0), GREEN),
    ]))
    story.append(tri)

    header = Table([
        [Paragraph("LEGAL METROLOGY COMPLIANCE REPORT", title_st)],
        [Paragraph("Ministry of Consumer Affairs, Food &amp; Public Distribution", sub_st)],
        [Paragraph("Legal Metrology (Packaged Commodities) Rules, 2011", sub_st)],
    ], colWidths=[W])
    header.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), NAVY),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    story.append(header)
    story.append(Spacer(1, 6*mm))

    # ═══════════════════════════════════════════════════════════════════════
    # 2. SCORE CARD (BIG + SIMPLE)
    # ═══════════════════════════════════════════════════════════════════════
    score_color = _score_color(sc)

    left_info = Table([
        [Paragraph("<b>Product Scanned</b>", bold_st), Paragraph(scan_id[:8].upper(), cell_st)],
        [Paragraph("<b>Report Date</b>",     bold_st), Paragraph(now, cell_st)],
        [Paragraph("<b>Total Issues Found</b>", bold_st),
         Paragraph(f"{len(violations)}", cell_st)],
        [Paragraph("<b>Severity Breakdown</b>", bold_st),
         Paragraph(
             f'<font color="#DC2626"><b>{high} High</b></font> &nbsp; '
             f'<font color="#D97706"><b>{medium} Medium</b></font> &nbsp; '
             f'<font color="#6B7280"><b>{low} Low</b></font>',
             cell_st,
         )],
    ], colWidths=[45*mm, 90*mm])
    left_info.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), GREY_BG),
        ("GRID", (0,0), (-1,-1), 0.4, GREY_BDR),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))

    score_card = Table([
        [Paragraph(f"{sc}", score_st)],
        [Paragraph("out of 100", score_lb)],
        [Paragraph(_score_label(sc), score_lb)],
    ], colWidths=[62*mm], rowHeights=[30*mm, 6*mm, 8*mm])
    score_card.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), score_color),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))

    score_row = Table([[left_info, score_card]], colWidths=[W-64*mm, 64*mm])
    score_row.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("ALIGN", (1,0), (1,0), "RIGHT"),
    ]))
    story.append(score_row)
    story.append(Spacer(1, 7*mm))

    # ═══════════════════════════════════════════════════════════════════════
    # 3. MANDATORY DECLARATIONS CHECKLIST (BIG ICONS)
    # ═══════════════════════════════════════════════════════════════════════
    story.append(Paragraph("1.  MANDATORY DECLARATIONS", h2_st))
    story.append(HRFlowable(width=W, thickness=1.2, color=NAVY, spaceAfter=4))

    field_map = {f.get("field_name"): f for f in fields}

    hdr = [
        Paragraph("<b>Status</b>", bold_st),
        Paragraph("<b>Declaration</b>", bold_st),
        Paragraph("<b>Extracted Value</b>", bold_st),
        Paragraph("<b>Rule</b>", bold_st),
    ]
    rows = [hdr]
    row_styles = []
    r_i = 0

    def render_field(key, label, rule):
        nonlocal r_i
        r_i += 1
        f = field_map.get(key)
        value = (f or {}).get("field_value") or ""
        has = bool(value)
        if has:
            icon, icon_col = "✓", GREEN
            bg = GREEN_BG
        else:
            icon, icon_col = "✗", RED
            bg = RED_BG
        val_display = value if value else "<i>NOT DECLARED</i>"
        if len(val_display) > 100:
            val_display = val_display[:100] + "…"
        rows.append([
            Paragraph(f'<font color="{"#15803D" if has else "#DC2626"}" size="16"><b>{icon}</b></font>',
                      S("ic", fontSize=14, alignment=TA_CENTER)),
            Paragraph(f"<b>{label}</b>", cell_st),
            Paragraph(val_display, cell_st),
            Paragraph(f'<font size="7" color="#6B7280">{rule}</font>', small_st),
        ])
        row_styles.append(("BACKGROUND", (0, r_i), (-1, r_i), bg))

    story.append(Paragraph("<b>Rule 6 Mandatory Fields</b>", S("sec", fontSize=10, textColor=NAVY, fontName="Helvetica-Bold", spaceAfter=3)))
    for k, label, rule in FIELD_ORDER:
        render_field(k, label, rule)

    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("<b>Additional Declarations</b>", S("sec", fontSize=10, textColor=NAVY, fontName="Helvetica-Bold", spaceAfter=3)))
    extra_shown = 0
    for k, label, rule in OPTIONAL_ORDER:
        if k in field_map and field_map[k].get("field_value"):
            render_field(k, label, rule)
            extra_shown += 1
    if extra_shown == 0:
        rows.append([
            Paragraph("—", S("dash", alignment=TA_CENTER, textColor=GREY_TXT)),
            Paragraph("<i>No additional declarations detected</i>", cell_st),
            Paragraph("", cell_st),
            Paragraph("", small_st),
        ])
        row_styles.append(("BACKGROUND", (0, r_i+1), (-1, r_i+1), GREY_BG))
        r_i += 1

    field_tbl = Table(rows, colWidths=[16*mm, 62*mm, 82*mm, 20*mm], repeatRows=1)
    field_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
        ("GRID",       (0, 0), (-1, -1), 0.4, GREY_BDR),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ] + row_styles))
    story.append(field_tbl)
    story.append(Spacer(1, 7*mm))

    # ═══════════════════════════════════════════════════════════════════════
    # 4. VIOLATIONS (numbered, plain english)
    # ═══════════════════════════════════════════════════════════════════════
    story.append(Paragraph("2.  VIOLATIONS FOUND", h2_st))
    story.append(HRFlowable(width=W, thickness=1.2, color=NAVY, spaceAfter=4))

    if not violations:
        ok = Table([[Paragraph(
            '<font color="#15803D" size="14"><b>✓  No violations found. Package is compliant.</b></font>',
            S("ok", fontSize=12, textColor=GREEN, alignment=TA_CENTER),
        )]], colWidths=[W])
        ok.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), GREEN_BG),
            ("TOPPADDING", (0,0), (-1,-1), 12),
            ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ]))
        story.append(ok)
    else:
        sev_order = {"high": 0, "medium": 1, "low": 2}
        sorted_v = sorted(violations, key=lambda v: sev_order.get(v.get("severity"), 3))

        for idx, v in enumerate(sorted_v, start=1):
            sev = v.get("severity", "low")
            code = v.get("rule_code", "")
            msg = v.get("message", "")
            if " | Ref: " in msg:
                desc, ref = msg.split(" | Ref: ", 1)
                ref = ref.replace(", LM(PC) Rules, 2011", "").strip()
            else:
                desc, ref = msg, "—"

            sev_col = {"high": RED, "medium": AMBER, "low": GREY_TXT}.get(sev, GREY_TXT)
            sev_bg  = {"high": RED_BG, "medium": AMBER_BG, "low": GREY_BG}.get(sev, GREY_BG)
            sev_lbl = {"high": "HIGH", "medium": "MEDIUM", "low": "LOW"}.get(sev, sev.upper())

            num_badge = Table([[Paragraph(
                f'<font color="white" size="14"><b>{idx}</b></font>',
                S("nb", fontSize=14, textColor=WHITE, alignment=TA_CENTER),
            )]], colWidths=[10*mm], rowHeights=[10*mm])
            num_badge.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,-1), NAVY),
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ]))

            info = Table([
                [Paragraph(f'<font color="{sev_col.hexval()[2:]}"><b>●  {sev_lbl} SEVERITY</b></font>', bold_st),
                 Paragraph(f'<font name="Courier" size="7" color="#6B7280">{code}</font>', mono_st)],
                [Paragraph(desc, body_st), ""],
                [Paragraph(f'<i>Legal Reference: {ref}</i>', small_st), ""],
            ], colWidths=[W - 34*mm, 28*mm])
            info.setStyle(TableStyle([
                ("SPAN", (0,1), (1,1)),
                ("SPAN", (0,2), (1,2)),
                ("BACKGROUND", (0,0), (-1,-1), sev_bg),
                ("LEFTPADDING", (0,0), (-1,-1), 10),
                ("RIGHTPADDING", (0,0), (-1,-1), 10),
                ("TOPPADDING", (0,0), (-1,-1), 4),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                ("ALIGN", (1,0), (1,0), "RIGHT"),
                ("VALIGN", (0,0), (-1,-1), "TOP"),
            ]))

            row = Table([[num_badge, info]], colWidths=[10*mm, W - 10*mm])
            row.setStyle(TableStyle([
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("LEFTPADDING", (0,0), (-1,-1), 0),
                ("RIGHTPADDING", (0,0), (-1,-1), 0),
                ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ]))
            story.append(row)
            story.append(Spacer(1, 2.5*mm))

    story.append(Spacer(1, 6*mm))

    # ═══════════════════════════════════════════════════════════════════════
    # 5. OFFICER ACTION BOX
    # ═══════════════════════════════════════════════════════════════════════
    if violations:
        action_box = Table([[Paragraph(
            "<b>RECOMMENDED ACTION:</b>  Issue notice under Section 33 of the Legal Metrology Act, 2009. "
            "Verify all violations against the physical package before initiating enforcement. "
            f"Priority: <b>{high} high-severity violations</b> require immediate action.",
            S("ab", fontSize=10, textColor=BLACK, leading=14),
        )]], colWidths=[W])
        action_box.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), AMBER_BG),
            ("BOX", (0,0), (-1,-1), 1, AMBER),
            ("TOPPADDING", (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
            ("LEFTPADDING", (0,0), (-1,-1), 12),
            ("RIGHTPADDING", (0,0), (-1,-1), 12),
        ]))
        story.append(action_box)
        story.append(Spacer(1, 5*mm))

    # ═══════════════════════════════════════════════════════════════════════
    # 6. FOOTER
    # ═══════════════════════════════════════════════════════════════════════
    story.append(HRFlowable(width=W, thickness=0.5, color=GREY_BDR))
    footer = Table([[
        Paragraph(
            f'<font size="7" color="#6B7280">Scan ID: {scan_id[:8].upper()} · {now}<br/>'
            f'SIH26034 · Legal Metrology Compliance Checker</font>',
            small_st,
        ),
        Paragraph(
            '<font size="7" color="#6B7280">Ministry of Consumer Affairs,<br/>'
            'Food &amp; Public Distribution</font>',
            S("fr", fontSize=7, textColor=GREY_TXT, alignment=TA_RIGHT, leading=11),
        ),
    ]], colWidths=[W/2, W/2])
    footer.setStyle(TableStyle([
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
    ]))
    story.append(footer)

    doc.build(story)
    return buf.getvalue()


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
        "scanId": scan_id,
        "score": round(score, 2),
        "status": (
            "compliant" if score >= 90 else
            "minor_violations" if score >= 70 else
            "major_violations" if score >= 50 else
            "non_compliant"
        ),
        "generatedAt": datetime.utcnow().isoformat() + "Z",
        "summary": {
            "totalViolations": len(violations),
            "highSeverity": high,
            "mediumSeverity": medium,
            "lowSeverity": low,
            "fieldsExtracted": sum(1 for f in fields if f.get("field_value")),
            "fieldsTotal": len(fields),
            "legalReference": "Legal Metrology (Packaged Commodities) Rules, 2011",
        },
        "fields": fields,
        "violations": violations,
    }
    return json.dumps(report, indent=2, default=str).encode("utf-8")