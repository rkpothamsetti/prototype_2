"""Image preprocessing pipeline."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from config import PROCESSED_DIR, ensure_dirs, settings
from schemas import PreprocessingMetadata
from services.common.utils import is_night_image, laplacian_variance


def _resize_long_edge(image: np.ndarray, max_edge: int) -> np.ndarray:
    h, w = image.shape[:2]
    long_edge = max(h, w)
    if long_edge <= max_edge:
        return image
    scale = max_edge / long_edge
    new_w = int(w * scale)
    new_h = int(h * scale)
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)


def _apply_clahe(image: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    merged = cv2.merge((l, a, b))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def _low_light_boost(image: np.ndarray) -> np.ndarray:
    gamma = 1.4
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype("uint8")
    return cv2.LUT(image, table)


def preprocess_frame(image: np.ndarray) -> tuple[np.ndarray, PreprocessingMetadata]:
    """In-memory preprocess without writing to disk (for video frames)."""
    original_h, original_w = image.shape[:2]
    processed = _resize_long_edge(image, settings.preprocess_max_edge)
    processed = _apply_clahe(processed)

    blur_var = laplacian_variance(processed)
    night = is_night_image(processed)
    enhancements: list[str] = ["clahe", "resize"]

    quality_score = min(1.0, blur_var / max(settings.blur_threshold, 1.0))
    if quality_score < 0.45 and night:
        processed = _low_light_boost(processed)
        enhancements.append("low_light_boost")
        quality_score = min(1.0, quality_score + 0.1)

    proc_h, proc_w = processed.shape[:2]
    metadata = PreprocessingMetadata(
        quality_score=round(quality_score, 4),
        blur_variance=round(blur_var, 2),
        night_detected=night,
        enhancements_applied=enhancements,
        original_size=[original_w, original_h],
        processed_size=[proc_w, proc_h],
    )
    return processed, metadata


def preprocess_image(image: np.ndarray, media_id: str) -> tuple[np.ndarray, PreprocessingMetadata, Path]:
    processed, metadata = preprocess_frame(image)
    out_path = PROCESSED_DIR / f"{media_id}_preprocessed.jpg"
    cv2.imwrite(str(out_path), processed)
    return processed, metadata, out_path
