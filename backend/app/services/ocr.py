"""
Fast OCR using Tesseract (pytesseract).
- No neural network loading = instant cold start
- 3-8 sec per image on free CPU (vs 45-90 sec with RapidOCR)
- Returns same block format as before so extraction.py unchanged
"""
from __future__ import annotations

import time
from typing import Any

import cv2
import numpy as np
import pytesseract

from app.core.logging import logger

# Tesseract config
# PSM 11 = sparse text (good for labels with mixed layout)
# PSM 3  = fully automatic (good for structured text)
_TSS_CONFIG_SPARSE = "--psm 11 --oem 1"
_TSS_CONFIG_AUTO   = "--psm 3  --oem 1"


def warmup_ocr() -> None:
    """Tesseract has no model load time — instant."""
    dummy = np.full((64, 256, 3), 255, dtype=np.uint8)
    try:
        pytesseract.image_to_string(dummy)
        logger.info("Tesseract OCR warmed up")
    except Exception as e:
        logger.warning(f"Tesseract warmup: {e}")


def _decode(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image")
    return img


def _preprocess_for_tess(img: np.ndarray) -> np.ndarray:
    """Sharpen + adaptive threshold for better Tesseract accuracy."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # CLAHE for contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    # Mild denoise
    gray = cv2.GaussianBlur(gray, (1, 1), 0)
    return gray


def run_ocr(image_bytes: bytes) -> list[dict[str, Any]]:
    img = _decode(image_bytes)
    h, w = img.shape[:2]
    t0 = time.time()

    gray = _preprocess_for_tess(img)

    # Get detailed data with bounding boxes
    data = pytesseract.image_to_data(
        gray,
        config=_TSS_CONFIG_AUTO,
        output_type=pytesseract.Output.DICT,
    )

    blocks: list[dict[str, Any]] = []
    n = len(data["text"])

    for i in range(n):
        text = str(data["text"][i]).strip()
        if not text:
            continue
        try:
            conf = float(data["conf"][i])
        except Exception:
            conf = 0.0
        if conf < 10:  # tesseract confidence 0-100, skip very low
            continue

        x = int(data["left"][i])
        y = int(data["top"][i])
        bw = int(data["width"][i])
        bh = int(data["height"][i])

        if bw < 2 or bh < 2:
            continue

        blocks.append({
            "text": text,
            "bbox": {"x": x, "y": y, "w": bw, "h": bh},
            "confidence": round(conf / 100.0, 4),  # normalize to 0-1
            "poly": [[x, y], [x+bw, y], [x+bw, y+bh], [x, y+bh]],
        })

    elapsed = time.time() - t0
    logger.info(f"Tesseract OCR: {w}x{h}px → {len(blocks)} blocks in {elapsed:.2f}s")

    blocks.sort(key=lambda b: (b["bbox"]["y"], b["bbox"]["x"]))
    return blocks


def ocr_stats(blocks: list[dict[str, Any]]) -> dict[str, float]:
    if not blocks:
        return {"n_blocks": 0, "mean_conf": 0.0, "text_chars": 0}
    confs = [b["confidence"] for b in blocks]
    return {
        "n_blocks": len(blocks),
        "mean_conf": round(sum(confs) / len(confs), 4),
        "text_chars": sum(len(b["text"]) for b in blocks),
    }