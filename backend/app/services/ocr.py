"""
Real OCR using RapidOCR (PP-OCRv4 via ONNX Runtime).
RAM + speed optimised for free tier.
"""
from __future__ import annotations

import os
import threading
import time
from typing import Any

import cv2
import numpy as np

from app.core.logging import logger

# Thread tuning (must be set before ONNX imports)
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("ORT_NUM_THREADS", "2")

_engine = None
_lock = threading.Lock()
_warmed = False

TEXT_SCORE = 0.30
BOX_THRESH = 0.40
UNCLIP_RATIO = 1.8
OCR_THREADS = 2


def _get_engine():
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                t0 = time.time()
                from rapidocr_onnxruntime import RapidOCR
                _engine = RapidOCR()
                logger.info(f"OCR engine loaded in {time.time() - t0:.2f}s")
    return _engine


def warmup_ocr() -> None:
    """Force-load the OCR engine once. Call at worker boot."""
    global _warmed
    if _warmed:
        return
    t0 = time.time()
    _get_engine()
    # Run a tiny dummy inference to warm ORT kernels
    dummy = np.full((64, 256, 3), 255, dtype=np.uint8)
    try:
        _get_engine()(dummy, use_det=True, use_cls=True, use_rec=True)
    except Exception:
        pass
    _warmed = True
    logger.info(f"OCR warmup complete in {time.time() - t0:.2f}s")


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
    return {
        "x": int(round(x0)), "y": int(round(y0)),
        "w": int(round(x1 - x0)), "h": int(round(y1 - y0)),
    }


def run_ocr(image_bytes: bytes) -> list[dict[str, Any]]:
    img = _decode(image_bytes)
    engine = _get_engine()

    h, w = img.shape[:2]
    t0 = time.time()

    result, _elapse = engine(
        img,
        use_det=True,
        use_cls=True,
        use_rec=True,
        text_score=TEXT_SCORE,
        box_thresh=BOX_THRESH,
        unclip_ratio=UNCLIP_RATIO,
    )

    elapsed = time.time() - t0
    n = len(result) if result else 0
    logger.info(f"OCR inference: {w}x{h}px, {n} blocks, {elapsed:.2f}s")

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