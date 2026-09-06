"""
Phase B: pixel-to-millimetre calibration.

Detects a standard ISO/IEC 7810 ID-1 card (credit/debit/PAN/Aadhaar PVC card:
85.60 x 53.98 mm) in the calibration image and returns mm_per_px.

Assumption (documented in the report): the calibration photo is taken at the
same distance/zoom as the label photos, so the scale is transferable.
"""
from __future__ import annotations

import cv2
import numpy as np

from app.services.preprocessing import load_oriented_bgr

CARD_LONG_MM = 85.60
CARD_SHORT_MM = 53.98
CARD_ASPECT = CARD_LONG_MM / CARD_SHORT_MM  # ~1.586
DETECT_SIDE = 1200


def estimate_mm_per_px(image_bytes: bytes) -> dict | None:
    img = load_oriented_bgr(image_bytes)
    H, W = img.shape[:2]
    m = max(H, W)
    s = DETECT_SIDE / m if m > DETECT_SIDE else 1.0
    small = cv2.resize(img, (int(W * s), int(H * s)), interpolation=cv2.INTER_AREA) if s != 1.0 else img

    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 50, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    img_area = small.shape[0] * small.shape[1]

    best = None
    for cnt in sorted(contours, key=cv2.contourArea, reverse=True):
        area = cv2.contourArea(cnt)
        if area < 0.02 * img_area:
            break
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) != 4 or not cv2.isContourConvex(approx):
            continue
        (cx, cy), (rw, rh), _ang = cv2.minAreaRect(approx)
        long_px, short_px = max(rw, rh), min(rw, rh)
        if short_px <= 0:
            continue
        ratio = long_px / short_px
        if 1.45 <= ratio <= 1.75:
            x, y, w, h = cv2.boundingRect(approx)
            best = {
                "long_px_detect": long_px,
                "ratio": ratio,
                "bbox": {"x": int(x / s), "y": int(y / s), "w": int(w / s), "h": int(h / s)},
            }
            break

    if not best:
        return None

    long_px_display = best["long_px_detect"] / s
    mm_per_px = CARD_LONG_MM / long_px_display
    conf = max(0.0, min(1.0, 1.0 - abs(best["ratio"] - CARD_ASPECT) / CARD_ASPECT * 4))
    return {
        "mm_per_px": round(mm_per_px, 6),
        "reference": "ISO/IEC 7810 ID-1 card (85.60 x 53.98 mm)",
        "bbox": best["bbox"],
        "confidence": round(conf, 3),
    }