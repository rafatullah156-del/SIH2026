"""
Preprocessing tuned for Tesseract accuracy on product labels.
- Higher resolution (1400px) — small legal text needs it
- Otsu binarization — Tesseract reads black/white far better than greyscale
- Denoise before threshold to avoid speckle
"""
from __future__ import annotations

import io
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageOps

MAX_SIDE = 1400        # legal text on back panel is small — needs resolution
MIN_SIDE = 900
BLUR_NORM_SIDE = 900
JPEG_QUALITY = 90       # binarized image compresses well regardless


@dataclass
class Prepared:
    working_bytes: bytes      # binarized image fed to OCR
    display_width: int
    display_height: int
    work_width: int
    work_height: int
    scale: float
    blur: float


def load_oriented_bgr(image_bytes: bytes) -> np.ndarray:
    pil = Image.open(io.BytesIO(image_bytes))
    pil = ImageOps.exif_transpose(pil)
    pil = pil.convert("RGB")
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def blur_score_bgr(img: np.ndarray) -> float:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    m = max(h, w)
    if m > BLUR_NORM_SIDE:
        s = BLUR_NORM_SIDE / m
        gray = cv2.resize(gray, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def blur_score(image_bytes: bytes) -> float:
    return blur_score_bgr(load_oriented_bgr(image_bytes))


def _binarize_for_tesseract(img: np.ndarray) -> np.ndarray:
    """
    Tesseract accuracy jumps massively on clean black/white text.
    Pipeline: grayscale -> denoise -> CLAHE -> Otsu threshold.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Denoise (removes JPEG/compression speckle that confuses Tesseract)
    gray = cv2.fastNlMeansDenoising(gray, h=8)

    # Local contrast boost before threshold
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # Otsu binarization — auto-picks best threshold
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Slight dilate to reconnect thin broken strokes from JPEG artefacts
    kernel = np.ones((1, 1), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    # Convert back to 3-channel so downstream code (which expects BGR) still works
    return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)


def prepare_image(image_bytes: bytes) -> Prepared:
    img = load_oriented_bgr(image_bytes)
    H, W = img.shape[:2]
    blur = blur_score_bgr(img)

    max_side = max(H, W)
    scale = 1.0
    if max_side > MAX_SIDE:
        scale = MAX_SIDE / max_side
        img = cv2.resize(
            img,
            (int(round(W * scale)), int(round(H * scale))),
            interpolation=cv2.INTER_AREA,
        )
    elif max_side < MIN_SIDE:
        scale = MIN_SIDE / max_side
        img = cv2.resize(
            img,
            (int(round(W * scale)), int(round(H * scale))),
            interpolation=cv2.INTER_CUBIC,
        )

    img = _binarize_for_tesseract(img)
    h, w = img.shape[:2]

    ok, buf = cv2.imencode(".png", img)  # PNG for binary images — lossless
    if not ok:
        raise ValueError("Failed to encode preprocessed image")

    return Prepared(
        working_bytes=buf.tobytes(),
        display_width=W,
        display_height=H,
        work_width=w,
        work_height=h,
        scale=scale,
        blur=round(blur, 2),
    )


def preprocess_image(image_bytes: bytes) -> bytes:
    return prepare_image(image_bytes).working_bytes


def map_bbox_to_display(bbox: dict | None, scale: float) -> dict | None:
    if not bbox or not scale:
        return bbox
    return {
        "x": int(round(bbox["x"] / scale)),
        "y": int(round(bbox["y"] / scale)),
        "w": int(round(bbox["w"] / scale)),
        "h": int(round(bbox["h"] / scale)),
    }