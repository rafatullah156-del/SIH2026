"""
Fast + low-RAM image preprocessing.
MAX_SIDE reduced to 640px for free-tier CPU speed.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageOps

MAX_SIDE = 640        # was 900 — 2x faster inference
MIN_SIDE = 480
BLUR_NORM_SIDE = 640
JPEG_QUALITY = 70


@dataclass
class Prepared:
    working_bytes: bytes
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


def _enhance(img: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)


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

    img = _enhance(img)
    h, w = img.shape[:2]

    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
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