"""
Phase B: rule-based entity extraction from OCR blocks.

Strategy
- Group OCR blocks into visual rows (label "MRP" and value "Rs. 199" are often
  separate boxes on the same line).
- Match lenient, OCR-error-tolerant patterns over the row text.
- Every extracted field carries: value, confidence, bbox (union of matched rows,
  in the same pixel space as the input blocks) and meta used by the rule engine.
- Mandatory fields are ALWAYS returned (value=None when not found) so the
  frontend can render a stable list. Optional extras only when found.

Output dict keys: field_name, field_value, confidence, panel_type,
                  scan_image_id, bbox, meta
"""
from __future__ import annotations

import re
import uuid
from typing import Any

MANDATORY_FIELDS = ["mrp", "net_quantity", "mfd_date", "manufacturer", "consumer_care"]

# ------------------------------------------------------------------ helpers

_DIGIT_FIX = str.maketrans({"O": "0", "o": "0", "B": "8"})


def _fix_digits(s: str) -> str:
    return s.translate(_DIGIT_FIX)


def _to_float(s: str) -> float | None:
    try:
        return float(_fix_digits(s).replace(",", ""))
    except Exception:
        return None


def _union(bboxes: list[dict]) -> dict | None:
    bboxes = [b for b in bboxes if b]
    if not bboxes:
        return None
    x0 = min(b["x"] for b in bboxes)
    y0 = min(b["y"] for b in bboxes)
    x1 = max(b["x"] + b["w"] for b in bboxes)
    y1 = max(b["y"] + b["h"] for b in bboxes)
    return {"x": int(x0), "y": int(y0), "w": int(x1 - x0), "h": int(y1 - y0)}


def build_rows(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group blocks into reading-order rows."""
    if not blocks:
        return []
    heights = sorted(max(1, b["bbox"]["h"]) for b in blocks)
    med_h = heights[len(heights) // 2]
    tol = med_h * 0.6

    items = sorted(blocks, key=lambda b: (b["bbox"]["y"] + b["bbox"]["h"] / 2, b["bbox"]["x"]))
    rows: list[dict[str, Any]] = []
    for b in items:
        cy = b["bbox"]["y"] + b["bbox"]["h"] / 2
        if rows and abs(cy - rows[-1]["cy"]) <= tol:
            r = rows[-1]
            r["blocks"].append(b)
            r["cy"] = (r["cy"] * (len(r["blocks"]) - 1) + cy) / len(r["blocks"])
        else:
            rows.append({"cy": cy, "blocks": [b]})

    for r in rows:
        r["blocks"].sort(key=lambda b: b["bbox"]["x"])
        r["text"] = " ".join(b["text"] for b in r["blocks"])
        r["bbox"] = _union([b["bbox"] for b in r["blocks"]])
        r["conf"] = sum(b["confidence"] for b in r["blocks"]) / len(r["blocks"])
    return rows


class _Doc:
    """Joined row text with offset -> row index mapping."""

    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows
        parts, spans, pos = [], [], 0
        for i, r in enumerate(rows):
            t = r["text"].upper()
            parts.append(t)
            spans.append((pos, pos + len(t), i))
            pos += len(t) + 1  # "\n"
        self.text = "\n".join(parts)
        self.spans = spans

    def rows_for(self, start: int, end: int) -> list[int]:
        return [i for (s, e, i) in self.spans if not (end <= s or start >= e)]

    def row_index_at(self, pos: int) -> int | None:
        for s, e, i in self.spans:
            if s <= pos <= e:
                return i
        return None

    def bbox(self, idxs: list[int]) -> dict | None:
        return _union([self.rows[i]["bbox"] for i in idxs])

    def conf(self, idxs: list[int]) -> float:
        if not idxs:
            return 0.0
        return sum(self.rows[i]["conf"] for i in idxs) / len(idxs)

    def block_bbox_containing(self, idxs: list[int], needle: str) -> dict | None:
        """bbox of the single OCR block that contains `needle` (e.g. the digits)."""
        n = needle.upper().replace(" ", "")
        for i in idxs:
            for b in self.rows[i]["blocks"]:
                if n and n in b["text"].upper().replace(" ", ""):
                    return b["bbox"]
        return None


def _field(name, value, conf, bbox, panel, image_id, meta=None):
    return {
        "field_name": name,
        "field_value": value,
        "confidence": round(float(max(0.0, min(1.0, conf))), 3),
        "panel_type": panel,
        "scan_image_id": str(image_id),
        "bbox": bbox,
        "meta": meta or {},
    }


# ------------------------------------------------------------------ patterns

_NUM = r"([0-9O]{1,3}(?:,[0-9O]{2,3})*(?:\.[0-9O]{1,2})?)"
_MRP_LABEL = r"(?:M\.?\s?R\.?\s?P\.?|MAX(?:IMUM)?\.?\s*RETAIL\s*PRICE|RETAIL\s*SALE\s*PRICE)"
_CUR = r"(?:RS\.?|R5\.?|R\$|INR|₹|`)"
MRP_RE = re.compile(_MRP_LABEL + r"(?:[^0-9\n]{0,45}\n?[^0-9\n]{0,20})?" + _NUM + r"(?:\s*/-)?")
MRP_FALLBACK_RE = re.compile(_CUR + r"\s*" + _NUM + r"(?:\s*/-)?")
TAX_TEXT_RE = re.compile(r"INCL|INCLUSIVE|ALL\s*TAX|OF\s*ALL\s*TAX")

_QTY = r"([0-9O]{1,5}(?:[.,][0-9O]{1,3})?)"
_UNIT = r"(KGS?|KILOGRAMS?|GMS?|GRAMS?|G|MG|MLS?|MILLILITRES?|MILLILITERS?|LTRS?|LITRES?|LITERS?|LT|L|PCS|PIECES?|NOS?|N|UNITS?|U)"
_NETQ_LABEL = r"(?:NET\s*(?:WT|WEIGHT|QTY|QUANTITY|CONTENTS?|VOL(?:UME)?)\.?|NET|CONTENTS?|QUANTITY|QTY)"
NETQ_RE = re.compile(_NETQ_LABEL + r"\s*[:\-\.]?\s*(?:E\s*)?" + _QTY + r"\s?" + _UNIT + r"\b")
QTY_FALLBACK_RE = re.compile(r"(?<![A-Z0-9/.])" + _QTY + r"\s?" + _UNIT + r"\b(?!\s*(?:/|PER|SERVING|EACH))")
_QTY_EXCLUDE_BEFORE = re.compile(r"(PER|/|EACH|SERVING|APPROX)\s*$")

_UNIT_NORM = {
    "KG": "kg", "KGS": "kg", "KILOGRAM": "kg", "KILOGRAMS": "kg",
    "G": "g", "GM": "g", "GMS": "g", "GRAM": "g", "GRAMS": "g", "MG": "mg",
    "ML": "ml", "MLS": "ml", "MILLILITRE": "ml", "MILLILITRES": "ml", "MILLILITER": "ml", "MILLILITERS": "ml",
    "L": "L", "LT": "L", "LTR": "L", "LTRS": "L", "LITRE": "L", "LITRES": "L", "LITER": "L", "LITERS": "L",
    "PCS": "pcs", "PIECE": "pcs", "PIECES": "pcs", "N": "N", "NO": "N", "NOS": "N", "UNIT": "units", "UNITS": "units", "U": "units",
}

_MON = r"(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|SEPT|OCT|NOV|DEC)"
_DATE_NUM = r"(?:[0-3]?\d[./\-])?(?:0?[1-9]|1[0-2])[./\-\s']?(?:20\d{2}|\d{2})\b"
_DATE_MON = r"(?:[0-3]?\d[\s./\-]*)?" + _MON + r"[A-Z]*\.?[\s./\-',]*(?:20\d{2}|\d{2})\b"
_DATE = r"((?:" + _DATE_MON + r")|(?:" + _DATE_NUM + r"))"
_MFD_LABEL = (
    r"(?:MFD|MFG|MF6|MANUFACTUR(?:ED|ING)(?:\s*(?:ON|IN|DATE))?|MANUFACTURE|"
    r"DATE\s*OF\s*(?:MFG|MANUFACTURE|MANUFACTURING|PACKING|PKG|PACKAGING|IMPORT)|"
    r"PKD|PACKED(?:\s*(?:ON|IN))?|PACKING\s*DATE|PKG\.?\s*DATE|IMPORTED(?:\s*(?:ON|IN))?|"
    r"DT\.?\s*OF\s*(?:MFG|PKG)|D\.?O\.?M\.?)"
)
MFD_RE = re.compile(_MFD_LABEL + r"[^\n0-9A-Z]{0,6}(?:DATE)?[^\n0-9]{0,15}" + _DATE)
MFD_LABEL_ONLY_RE = re.compile(_MFD_LABEL + r"\b")
DATE_ANY_RE = re.compile(_DATE)
_NOT_MFD_BEFORE = re.compile(r"(BEST\s*BEFORE|EXP(?:IRY)?|USE\s*BY|BB|EXPIRES?)[^\n]{0,20}$")
BEST_BEFORE_RE = re.compile(r"(?:BEST\s*BEFORE|USE\s*BY|EXP(?:IRY)?\.?\s*(?:DATE)?)\s*[:\-]?\s*([^\n]{3,40})")

_MFR_LABEL = (
    r"(?:MANUFACTURED\s*(?:AND|&)?\s*(?:PACKED\s*)?BY|MFD\.?\s*(?:&\s*PKD\.?\s*)?BY|MFG\.?\s*BY|"
    r"PACKED\s*BY|PKD\.?\s*BY|MARKETED\s*BY|MKTD\.?\s*BY|IMPORTED\s*(?:AND|&)?\s*(?:MARKETED\s*)?BY|"
    r"IMPORTER|MANUFACTURER|PACKER|DISTRIBUTED\s*BY|MADE\s*BY)"
)
MFR_RE = re.compile(_MFR_LABEL + r"\s*[:\-]?\s*")
_MFR_STOP = re.compile(
    r"^(?:CUSTOMER|CONSUMER|FOR\s*(?:FEEDBACK|COMPLAINTS?|QUERIES)|MRP|M\.R\.P|NET\s|BEST\s*BEFORE|MFD|MFG|PKD|EXP|"
    r"USE\s*BY|BATCH|LOT|FSSAI|LIC|INGREDIENTS|NUTRITION|STORAGE|STORE\s|KEEP\s|E-?MAIL|TOLL|HELPLINE|WWW\.)"
)
PIN_RE = re.compile(r"\b[1-9]\d{5}\b")
ENTITY_RE = re.compile(r"\b(PVT|PRIVATE|LTD|LIMITED|LLP|INC|CO\.|COMPANY|INDUSTRIES|ENTERPRISES|FOODS|PRODUCTS|CORPORATION|MILLS|AGRO|DAIRY)\b")

_CARE_LABEL = (
    r"(?:(?:CUSTOMER|CONSUMER)\s*(?:CARE|SERVICE|SUPPORT|HELPLINE|FEEDBACK|COMPLAINTS?)|"
    r"FOR\s*(?:ANY\s*)?(?:FEEDBACK|COMPLAINTS?|QUERIES|QUERY|ASSISTANCE|SUGGESTIONS?)|TOLL\s*FREE|HELPLINE|"
    r"CONTACT\s*US|WRITE\s*TO\s*US|REACH\s*US|CALL\s*US|E-?MAIL|EMAIL)"
)
CARE_LABEL_RE = re.compile(_CARE_LABEL)
PHONE_RE = re.compile(
    r"(?:1\s?800[\s\-]?\d{2,3}[\s\-]?\d{3,4}(?:[\s\-]?\d{1,4})?"
    r"|(?:\+?91[\s\-]?)?[6-9]\d{2}[\s\-]?\d{3}[\s\-]?\d{4}"
    r"|0\d{2,4}[\s\-]?\d{6,8})"
)
EMAIL_RE = re.compile(r"[A-Z0-9._%+\-]+\s?@\s?[A-Z0-9.\-]+\s?\.\s?[A-Z]{2,}")

FSSAI_RE = re.compile(r"FSSAI[^\d\n]{0,25}([0-9O]{14})")
BATCH_RE = re.compile(r"(?:BATCH|LOT|B\.?\s*NO)\.?\s*(?:NO\.?)?\s*[:\-]?\s*([A-Z0-9\-/]{3,20})")
ORIGIN_RE = re.compile(r"(?:COUNTRY\s*OF\s*ORIGIN|MADE\s*IN|PRODUCT\s*OF)\s*[:\-]?\s*([A-Z][A-Z ]{2,30})")


# ------------------------------------------------------------------ extractors

def _extract_mrp(doc: _Doc, panel, image_id):
    text = text_norm(doc.text)
    for m in MRP_RE.finditer(text):
        amt = _to_float(m.group(1))
        if amt is None or not (0.5 <= amt <= 100000):
            continue
        idxs = doc.rows_for(m.start(), m.end())
        neigh = set(idxs)
        for i in list(idxs):
            neigh.update({max(0, i - 1), min(len(doc.rows) - 1, i + 1)})
        near_text = " ".join(doc.rows[i]["text"].upper() for i in sorted(neigh))
        tax = bool(TAX_TEXT_RE.search(near_text))
        conf = doc.conf(idxs) * 0.98
        return _field("mrp", f"₹{amt:.2f}", conf, doc.bbox(idxs), panel, image_id,
                      {"amount": amt, "label_found": True, "tax_text_found": tax,
                       "value_bbox": doc.block_bbox_containing(idxs, m.group(1))})
    for m in MRP_FALLBACK_RE.finditer(text):
        amt = _to_float(m.group(1))
        if amt is None or not (0.5 <= amt <= 100000):
            continue
        idxs = doc.rows_for(m.start(), m.end())
        near_text = " ".join(doc.rows[i]["text"].upper() for i in idxs)
        return _field("mrp", f"₹{amt:.2f}", doc.conf(idxs) * 0.6, doc.bbox(idxs), panel, image_id,
                      {"amount": amt, "label_found": False, "tax_text_found": bool(TAX_TEXT_RE.search(near_text)),
                       "value_bbox": doc.block_bbox_containing(idxs, m.group(1))})
    return _field("mrp", None, 0.0, None, panel, image_id, {"label_found": False})


def text_norm(t: str) -> str:
    return t.replace("₹", " RS ").replace("R$", " RS ")


def _qty_meta(num_s: str, unit_s: str) -> dict | None:
    val = _to_float(num_s)
    unit = _UNIT_NORM.get(unit_s.upper())
    if val is None or unit is None or val <= 0:
        return None
    base = None
    if unit == "kg":
        base = val * 1000
    elif unit == "g":
        base = val
    elif unit == "L":
        base = val * 1000
    elif unit == "ml":
        base = val
    return {"value": val, "unit": unit, "base_g_or_ml": base}


def _extract_net_qty(doc: _Doc, panel, image_id):
    text = doc.text
    for m in NETQ_RE.finditer(text):
        meta = _qty_meta(m.group(1), m.group(2))
        if not meta:
            continue
        idxs = doc.rows_for(m.start(), m.end())
        meta.update({"label_found": True, "value_bbox": doc.block_bbox_containing(idxs, m.group(1))})
        v = f"{meta['value']:g} {meta['unit']}"
        return _field("net_quantity", v, doc.conf(idxs) * 0.98, doc.bbox(idxs), panel, image_id, meta)

    # fallback: most prominent "<number> <unit>" not in a nutrition/serving context
    cands = []
    for m in QTY_FALLBACK_RE.finditer(text):
        before = text[max(0, m.start() - 14):m.start()]
        if _QTY_EXCLUDE_BEFORE.search(before):
            continue
        meta = _qty_meta(m.group(1), m.group(2))
        if not meta:
            continue
        idxs = doc.rows_for(m.start(), m.end())
        bb = doc.bbox(idxs)
        cands.append((bb["h"] if bb else 0, m, meta, idxs))
    if cands:
        cands.sort(key=lambda c: c[0], reverse=True)
        _, m, meta, idxs = cands[0]
        meta.update({"label_found": False, "value_bbox": doc.block_bbox_containing(idxs, m.group(1))})
        v = f"{meta['value']:g} {meta['unit']}"
        return _field("net_quantity", v, doc.conf(idxs) * 0.62, doc.bbox(idxs), panel, image_id, meta)

    return _field("net_quantity", None, 0.0, None, panel, image_id, {"label_found": False})


def _extract_mfd(doc: _Doc, panel, image_id):
    text = doc.text
    for m in MFD_RE.finditer(text):
        idxs = doc.rows_for(m.start(), m.end())
        return _field("mfd_date", m.group(1).strip(), doc.conf(idxs) * 0.97, doc.bbox(idxs), panel, image_id,
                      {"label_found": True})
    label = MFD_LABEL_ONLY_RE.search(text)
    for m in DATE_ANY_RE.finditer(text):
        before = text[max(0, m.start() - 30):m.start()]
        if _NOT_MFD_BEFORE.search(before):
            continue
        idxs = doc.rows_for(m.start(), m.end())
        return _field("mfd_date", m.group(1).strip(), doc.conf(idxs) * 0.5, doc.bbox(idxs), panel, image_id,
                      {"label_found": bool(label), "unlabelled_date": True})
    if label:
        idxs = doc.rows_for(label.start(), label.end())
        return _field("mfd_date", None, 0.0, doc.bbox(idxs), panel, image_id,
                      {"label_found": True, "note": "label present but date not readable"})
    return _field("mfd_date", None, 0.0, None, panel, image_id, {"label_found": False})


def _collect_after(doc: _Doc, start_pos: int, max_rows: int = 4, max_chars: int = 240) -> tuple[str, list[int]]:
    first = doc.row_index_at(start_pos)
    if first is None:
        return "", []
    s0 = doc.spans[first][0]
    parts = [doc.text[start_pos:doc.spans[first][1]].strip()]
    idxs = [first]
    total = len(parts[0])
    for i in range(first + 1, min(len(doc.rows), first + max_rows)):
        t = doc.rows[i]["text"].upper().strip()
        if not t or _MFR_STOP.search(t) or total + len(t) > max_chars:
            break
        parts.append(t)
        idxs.append(i)
        total += len(t)
    return ", ".join(p for p in parts if p), idxs


def _extract_manufacturer(doc: _Doc, panel, image_id):
    text = doc.text
    best = None
    for m in MFR_RE.finditer(text):
        body, idxs = _collect_after(doc, m.end())
        body = re.sub(r"\s+", " ", body).strip(" ,:-")
        if len(body) < 6:
            continue
        pin = PIN_RE.search(body)
        entity = ENTITY_RE.search(body)
        complete = bool(pin) or (bool(entity) and len(body) >= 25 and "," in body)
        conf = doc.conf(idxs) * (0.95 if complete else 0.7)
        cand = _field("manufacturer", body.title(), conf, doc.bbox(idxs), panel, image_id,
                      {"label_found": True, "pin_found": bool(pin), "entity_found": bool(entity),
                       "address_complete": complete, "label": m.group(0).strip()})
        if best is None or cand["confidence"] > best["confidence"]:
            best = cand
    if best:
        return best
    # fallback: row(s) with company suffix + PIN
    for i, r in enumerate(doc.rows):
        t = r["text"].upper()
        if ENTITY_RE.search(t):
            idxs = [i] + ([i + 1] if i + 1 < len(doc.rows) else [])
            body = ", ".join(doc.rows[j]["text"] for j in idxs)
            pin = PIN_RE.search(body.upper())
            return _field("manufacturer", body.title(), doc.conf(idxs) * (0.6 if pin else 0.45), doc.bbox(idxs),
                          panel, image_id, {"label_found": False, "pin_found": bool(pin), "entity_found": True,
                                            "address_complete": bool(pin)})
    return _field("manufacturer", None, 0.0, None, panel, image_id, {"label_found": False})


def _extract_consumer_care(doc: _Doc, panel, image_id):
    text = re.sub(r"1\s?8[O0]{2}", "1800", doc.text)
    phones, emails, idxs = [], [], set()
    for m in PHONE_RE.finditer(text):
        phones.append(re.sub(r"\s+", "", m.group(0)))
        idxs.update(doc.rows_for(m.start(), m.end()))
    for m in EMAIL_RE.finditer(text):
        emails.append(m.group(0).replace(" ", "").lower())
        idxs.update(doc.rows_for(m.start(), m.end()))
    label = CARE_LABEL_RE.search(text)
    if label:
        idxs.update(doc.rows_for(label.start(), label.end()))
    idxs_l = sorted(idxs)

    if phones or emails:
        parts = []
        if phones:
            parts.append("Ph: " + ", ".join(dict.fromkeys(phones[:2])))
        if emails:
            parts.append("Email: " + ", ".join(dict.fromkeys(emails[:2])))
        conf = doc.conf(idxs_l) * (0.95 if label else 0.65)
        return _field("consumer_care", "; ".join(parts), conf, doc.bbox(idxs_l), panel, image_id,
                      {"label_found": bool(label), "phones": phones[:3], "emails": emails[:3]})
    if label:
        return _field("consumer_care", None, 0.0, doc.bbox(idxs_l), panel, image_id,
                      {"label_found": True, "note": "label present but no phone/email readable"})
    return _field("consumer_care", None, 0.0, None, panel, image_id, {"label_found": False})


def _extract_optional(doc: _Doc, panel, image_id) -> list[dict]:
    out = []
    text = doc.text
    m = FSSAI_RE.search(text)
    if m:
        idxs = doc.rows_for(m.start(), m.end())
        out.append(_field("fssai_license", _fix_digits(m.group(1)), doc.conf(idxs), doc.bbox(idxs), panel, image_id, {"optional": True}))
    m = BATCH_RE.search(text)
    if m:
        idxs = doc.rows_for(m.start(), m.end())
        out.append(_field("batch_no", m.group(1), doc.conf(idxs) * 0.85, doc.bbox(idxs), panel, image_id, {"optional": True}))
    m = BEST_BEFORE_RE.search(text)
    if m:
        idxs = doc.rows_for(m.start(), m.end())
        out.append(_field("best_before", m.group(1).strip().title(), doc.conf(idxs) * 0.85, doc.bbox(idxs), panel, image_id, {"optional": True}))
    m = ORIGIN_RE.search(text)
    if m:
        idxs = doc.rows_for(m.start(), m.end())
        out.append(_field("country_of_origin", m.group(1).strip().title(), doc.conf(idxs) * 0.85, doc.bbox(idxs), panel, image_id, {"optional": True}))
    return out


# ------------------------------------------------------------------ public

def extract_fields(
    ocr_blocks: list[dict[str, Any]],
    panel_type: str,
    image_id: uuid.UUID,
) -> list[dict[str, Any]]:
    rows = build_rows(ocr_blocks)
    doc = _Doc(rows)
    fields = [
        _extract_mrp(doc, panel_type, image_id),
        _extract_net_qty(doc, panel_type, image_id),
        _extract_mfd(doc, panel_type, image_id),
        _extract_manufacturer(doc, panel_type, image_id),
        _extract_consumer_care(doc, panel_type, image_id),
    ]
    fields.extend(_extract_optional(doc, panel_type, image_id))
    return fields