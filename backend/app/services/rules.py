"""
Phase B: config-driven compliance rule engine (scan-level, evidence-first).

Three outcomes per check:
  PASS        -> nothing emitted
  VIOLATION   -> severity high/medium (confident, image readable)
  NEEDS_REVIEW-> severity low, rule_code ends with "_REVIEW"
                 (field missing but image quality poor / OCR unsure /
                  ambiguous). This prevents false "faults".

Legal references: Legal Metrology (Packaged Commodities) Rules, 2011.
"""
from __future__ import annotations

from typing import Any

LEGAL = "LM(PC) Rules, 2011"

# quality gates
BLUR_MIN = 60.0        # below this an image is considered blurred
CONF_OK = 0.60         # field confidence at/above this = confident
IMG_CONF_MIN = 0.55    # mean OCR confidence for an image to count as readable
MIN_BLOCKS = 5         # fewer text blocks than this => likely not a label / unreadable

RULES: dict[str, dict[str, Any]] = {
    "mrp": {
        "label": "Retail sale price (MRP)",
        "code": "MRP_MISSING",
        "severity": "high",
        "ref": "Rule 6(1)(e) r/w Rule 2(m)",
        "message": "Retail sale price (MRP) not declared on the package",
        "pdp": True,
    },
    "net_quantity": {
        "label": "Net quantity",
        "code": "NET_QTY_MISSING",
        "severity": "high",
        "ref": "Rule 6(1)(c) r/w Rule 8",
        "message": "Net quantity (with standard unit) not declared on the package",
        "pdp": True,
    },
    "mfd_date": {
        "label": "Month & year of manufacture/packing/import",
        "code": "MFD_MISSING",
        "severity": "high",
        "ref": "Rule 6(1)(d)",
        "message": "Month and year of manufacture / pre-packing / import not declared",
        "pdp": False,
    },
    "manufacturer": {
        "label": "Name & address of manufacturer/packer/importer",
        "code": "MANUFACTURER_MISSING",
        "severity": "high",
        "ref": "Rule 6(1)(a)",
        "message": "Name and complete address of manufacturer / packer / importer not declared",
        "pdp": False,
    },
    "consumer_care": {
        "label": "Consumer care details",
        "code": "CONSUMER_CARE_MISSING",
        "severity": "medium",
        "ref": "Rule 6(1)(f)",
        "message": "Consumer care telephone number / e-mail address not declared",
        "pdp": False,
    },
}

# Rule 8 table: minimum height of numerals in net quantity declaration (normal packages)
NET_QTY_NUMERAL_MM = [(200, 1.0), (500, 2.0), (float("inf"), 4.0)]

SCORE_PENALTY = {"high": 20, "medium": 10, "low": 3}


def _v(code, severity, field, message, ref, where, bbox=None):
    return {
        "rule_code": code,
        "severity": severity,
        "field": field,
        "message": f"{message} | Ref: {ref}, {LEGAL}",
        "panel_type": where.get("panel_type"),
        "scan_image_id": where.get("scan_image_id"),
        "bbox": bbox,
    }


def _where(field: dict | None, default: dict) -> dict:
    if field and field.get("scan_image_id"):
        return {"panel_type": field.get("panel_type"), "scan_image_id": field.get("scan_image_id")}
    return default


def image_readable(q: dict) -> bool:
    return q["blur"] >= BLUR_MIN and q["mean_conf"] >= IMG_CONF_MIN and q["n_blocks"] >= MIN_BLOCKS


def run_rules(
    fields: dict[str, dict[str, Any]],
    *,
    panel_presence: dict[str, set[str]],
    image_quality: list[dict[str, Any]],
    mm_per_px: float | None,
    calibration_note: str | None,
    default_where: dict[str, Any],
) -> tuple[list[dict[str, Any]], float]:
    """
    fields          : merged best field per field_name (value may be None)
    panel_presence  : field_name -> set of panels where found with conf >= 0.5
    image_quality   : [{scan_image_id, panel_type, blur, mean_conf, n_blocks}] (label panels only)
    mm_per_px       : from calibration (None if unavailable)
    default_where   : {panel_type, scan_image_id} used for scan-level findings (front image)
    """
    violations: list[dict[str, Any]] = []
    readable_any = any(image_readable(q) for q in image_quality)

    # ---- 1) Readability per image (Rule 9)
    for q in image_quality:
        where = {"panel_type": q["panel_type"], "scan_image_id": q["scan_image_id"]}
        if q["n_blocks"] == 0:
            violations.append(_v("NO_TEXT_DETECTED_REVIEW", "low", None,
                                 f"No readable text detected on {q['panel_type']} panel image — retake photo",
                                 "Rule 9(1)", where))
        elif q["blur"] < BLUR_MIN:
            violations.append(_v("LOW_READABILITY", "low", None,
                                 f"{q['panel_type'].capitalize()} panel image appears blurred (sharpness {q['blur']:.0f}); "
                                 f"declarations may not be legible — retake recommended",
                                 "Rule 9(1)", where))
        elif q["mean_conf"] < IMG_CONF_MIN:
            violations.append(_v("LOW_OCR_CONFIDENCE_REVIEW", "low", None,
                                 f"Text on {q['panel_type']} panel recognised with low confidence "
                                 f"({q['mean_conf']:.0%}); verify manually",
                                 "Rule 9(1)", where))

    # ---- 2) Mandatory declarations (Rule 6)
    for name, rule in RULES.items():
        f = fields.get(name)
        value = f.get("field_value") if f else None
        conf = float(f.get("confidence") or 0.0) if f else 0.0
        meta = (f or {}).get("meta") or {}
        where = _where(f, default_where)
        bbox = (f or {}).get("bbox")

        if value and conf >= CONF_OK:
            continue  # PASS

        if value and conf < CONF_OK:
            violations.append(_v(f"{rule['code']}_REVIEW", "low", name,
                                 f"{rule['label']} detected as '{value}' but with low confidence ({conf:.0%}); "
                                 f"verify against the physical label", rule["ref"], where, bbox))
            continue

        # value is None
        if meta.get("label_found"):
            violations.append(_v(f"{rule['code']}_REVIEW", "low", name,
                                 f"'{rule['label']}' label is present but its value could not be read; verify manually",
                                 rule["ref"], where, bbox))
        elif readable_any:
            violations.append(_v(rule["code"], rule["severity"], name, rule["message"], rule["ref"],
                                 default_where, None))
        else:
            violations.append(_v(f"{rule['code']}_REVIEW", "low", name,
                                 f"{rule['label']} could not be verified — image quality insufficient for automated check",
                                 rule["ref"], default_where, None))

    # ---- 3) MRP wording: "inclusive of all taxes" (Rule 2(m) / 6(1)(e))
    mrp = fields.get("mrp")
    if mrp and mrp.get("field_value") and float(mrp.get("confidence") or 0) >= CONF_OK:
        if not (mrp.get("meta") or {}).get("tax_text_found"):
            violations.append(_v("MRP_TAX_TEXT_REVIEW", "low", "mrp",
                                 "Statement 'inclusive of all taxes' not detected alongside MRP; verify wording",
                                 "Rule 2(m) r/w Rule 6(1)(e)", _where(mrp, default_where), mrp.get("bbox")))

    # ---- 4) Manufacturer address completeness (Rule 6(1)(a))
    mfr = fields.get("manufacturer")
    if mfr and mfr.get("field_value") and float(mfr.get("confidence") or 0) >= CONF_OK:
        if not (mfr.get("meta") or {}).get("address_complete"):
            violations.append(_v("MANUFACTURER_ADDRESS_INCOMPLETE_REVIEW", "low", "manufacturer",
                                 "Manufacturer/packer address appears incomplete (no PIN code / locality detected); verify",
                                 "Rule 6(1)(a) r/w Rule 2(a)", _where(mfr, default_where), mfr.get("bbox")))

    # ---- 5) Placement: MRP & net quantity expected on principal display panel (Rule 7)
    for name, rule in RULES.items():
        if not rule["pdp"]:
            continue
        panels = panel_presence.get(name) or set()
        if panels and "front" not in panels:
            f = fields.get(name)
            violations.append(_v(f"{rule['code'].replace('_MISSING', '')}_PLACEMENT_REVIEW", "low", name,
                                 f"{rule['label']} found on {'/'.join(sorted(panels))} panel only; "
                                 f"declarations should be grouped on the principal display panel — verify",
                                 "Rule 7", _where(f, default_where), (f or {}).get("bbox")))

    # ---- 6) Net quantity numeral height (Rule 8) — needs calibration
    nq = fields.get("net_quantity")
    if nq and nq.get("field_value"):
        meta = nq.get("meta") or {}
        vb = meta.get("value_bbox") or nq.get("bbox")
        base = meta.get("base_g_or_ml")
        if mm_per_px and vb and base is not None:
            required = next(mm for lim, mm in NET_QTY_NUMERAL_MM if base <= lim)
            est_mm = vb["h"] * mm_per_px * 0.70  # cap-height ≈ 70% of OCR box height
            where = _where(nq, default_where)
            if est_mm < required * 0.6:
                violations.append(_v("NET_QTY_NUMERAL_HEIGHT", "medium", "net_quantity",
                                     f"Net quantity numerals estimated at {est_mm:.1f} mm; minimum required is {required:.0f} mm "
                                     f"for {base:g} g/ml packages", "Rule 8 (Table)", where, vb))
            elif est_mm < required:
                violations.append(_v("NET_QTY_NUMERAL_HEIGHT_REVIEW", "low", "net_quantity",
                                     f"Net quantity numerals estimated at {est_mm:.1f} mm (required {required:.0f} mm); "
                                     f"borderline — verify with physical measurement", "Rule 8 (Table)", where, vb))
        elif calibration_note:
            violations.append(_v("FONT_SIZE_NOT_CHECKED_REVIEW", "low", "net_quantity",
                                 f"Numeral height not verified: {calibration_note}", "Rule 8", default_where))

    # ---- Score
    score = 100.0
    for v in violations:
        score -= SCORE_PENALTY.get(v["severity"], 0)
    return violations, round(max(0.0, score), 2)