"""
Phase B: real OCR using PaddleOCR PP-OCRv4 models executed via ONNX Runtime
(rapidocr-onnxruntime). Models are bundled in the wheel: no runtime download.

Returns OCR blocks in the locked contract:
  {"text": str, "bbox": {"x","y","w","h"}, "confidence": float, "poly": [[x,y]x4]}
bbox coordinates are in pixels of the image passed in.
"""
from __future__ import annotations

import threading
from typing import Any

import cv2
import numpy as np

from app.core.logging import logger

_engine = None
_lock = threading.Lock()

# Recognition score floor. We keep low-confidence text on purpose: the rule
# engine decides how to treat uncertainty (review instead of violation).
TEXT_SCORE = 0.30
BOX_THRESH = 0.40
UNCLIP_RATIO = 1.8


def _get_engine():
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                from rapidocr_onnxruntime import RapidOCR
                _engine = RapidOCR()
                logger.info("OCR engine loaded (PP-OCRv4 det+cls+rec via ONNX Runtime)")
    return _engine


def _decode(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image for OCR")
    return img


def _poly_to_rect(poly) -> dict[str, int]:
    xs = [float(p[0]) for p in poly]
    ys = [float(p[1]) for p in poly]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    return {"x": int(round(x0)), "y": int(round(y0)), "w": int(round(x1 - x0)), "h": int(round(y1 - y0))}


def run_ocr(image_bytes: bytes) -> list[dict[str, Any]]:
    img = _decode(image_bytes)
    engine = _get_engine()

    result, _elapse = engine(
        img,
        use_det=True,
        use_cls=True,
        use_rec=True,
        text_score=TEXT_SCORE,
        box_thresh=BOX_THRESH,
        unclip_ratio=UNCLIP_RATIO,
    )

    blocks: list[dict[str, Any]] = []
    if not result:
        return blocks

    for item in result:
        try:
            poly, text, score = item[0], item[1], item[2]
        except Exception:
            continue
        text = str(text).strip()
        if not text:
            continue
        try:
            conf = float(score)
        except Exception:
            conf = 0.0
        rect = _poly_to_rect(poly)
        if rect["w"] < 2 or rect["h"] < 2:
            continue
        blocks.append({
            "text": text,
            "bbox": rect,
            "confidence": round(conf, 4),
            "poly": [[int(round(float(p[0]))), int(round(float(p[1])))] for p in poly],
        })

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