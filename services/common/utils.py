"""Geometry and image utility helpers."""
from __future__ import annotations

import math
import re
from typing import Iterable

import cv2
import numpy as np


def iou(box_a: list[float], box_b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter = inter_w * inter_h
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def point_in_rect(px: float, py: float, rect: list[float]) -> bool:
    x1, y1, x2, y2 = rect
    return x1 <= px <= x2 and y1 <= py <= y2


def center_of_bbox(bbox: list[float]) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def bbox_orientation_deg(bbox: list[float]) -> float:
    x1, y1, x2, y2 = bbox
    width = x2 - x1
    height = y2 - y1
    if width >= height:
        return 0.0
    return 90.0


def angle_difference(a: float, b: float) -> float:
    diff = abs(a - b) % 360.0
    return min(diff, 360.0 - diff)


def overlap_fraction(inner: list[float], outer: list[float]) -> float:
    ax1, ay1, ax2, ay2 = inner
    bx1, by1, bx2, by2 = outer
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter = inter_w * inter_h
    inner_area = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    if inner_area <= 0:
        return 0.0
    return inter / inner_area


def head_roi_from_person(
    person_bbox: list[float],
    image_shape: tuple[int, ...] | None = None,
) -> list[float]:
    """Head + helmet ROI. Extends above person bbox when room allows.

    When the person box starts near the image top, upward extension clamps to
    background and poisons helmet scoring — use the upper face band only instead.
    """
    x1, y1, x2, y2 = person_bbox
    h = max(y2 - y1, 1.0)
    w = max(x2 - x1, 1.0)
    img_h = image_shape[0] if image_shape is not None and len(image_shape) >= 1 else None
    near_top = img_h is not None and y1 < img_h * 0.15
    would_clamp = y1 - h * 0.45 < 0
    if near_top or would_clamp:
        return [
            x1 - w * 0.08,
            y1,
            x2 + w * 0.08,
            y1 + h * 0.38,
        ]
    return [
        x1 - w * 0.12,
        y1 - h * 0.45,
        x2 + w * 0.12,
        y1 + h * 0.40,
    ]


def head_rois_from_person(
    person_bbox: list[float],
    image_shape: tuple[int, ...] | None = None,
) -> list[list[float]]:
    """One or more head ROIs — split tall stacked-rider boxes (adult + child)."""
    x1, y1, x2, y2 = person_bbox
    h = max(y2 - y1, 1.0)
    w = max(x2 - x1, 1.0)

    if h > w * 1.48 and h > 260:
        pad_x = w * 0.08
        bands = ((0.0, 0.30), (0.22, 0.48))
        return [
            [x1 - pad_x, y1 + h * t0, x2 + pad_x, y1 + h * t1]
            for t0, t1 in bands
        ]

    return [head_roi_from_person(person_bbox, image_shape)]


def vehicle_plate_roi(vehicle_bbox: list[float]) -> list[float]:
    x1, y1, x2, y2 = vehicle_bbox
    w = x2 - x1
    h = y2 - y1
    return [x1 + w * 0.15, y1 + h * 0.55, x2 - w * 0.15, y2 - h * 0.05]


def normalize_indian_plate(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", text.upper())
    return cleaned


def validate_indian_plate(plate: str, pattern: str) -> bool:
    return bool(re.match(pattern, plate))


def clamp_bbox(bbox: list[float], width: int, height: int) -> list[float]:
    x1, y1, x2, y2 = bbox
    return [
        float(max(0, min(width - 1, x1))),
        float(max(0, min(height - 1, y1))),
        float(max(0, min(width - 1, x2))),
        float(max(0, min(height - 1, y2))),
    ]


def crop_image(image: np.ndarray, bbox: list[float]) -> np.ndarray:
    h, w = image.shape[:2]
    x1, y1, x2, y2 = [int(v) for v in clamp_bbox(bbox, w, h)]
    if x2 <= x1 or y2 <= y1:
        return image[0:1, 0:1]
    return image[y1:y2, x1:x2]


def laplacian_variance(image: np.ndarray) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def is_night_image(image: np.ndarray) -> bool:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(np.mean(gray)) < 70.0


def quality_factor_from_score(score: float, min_factor: float = 0.7, max_factor: float = 1.0) -> float:
    return min_factor + (max_factor - min_factor) * max(0.0, min(1.0, score))


def mean_confidence(values: Iterable[float], default: float = 0.5) -> float:
    vals = list(values)
    if not vals:
        return default
    return float(sum(vals) / len(vals))
