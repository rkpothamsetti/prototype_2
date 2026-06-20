"""Unified helmet assessment: YOLO detector + heuristic fallback."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from schemas import Detection
from services.common.utils import head_roi_from_person, head_rois_from_person
from services.detection.helmet_yolo import (
    detect_helmet_objects,
    helmet_model_available,
    yolo_worst_helmet_score_for_person,
)
from services.violation_reasoning.helmet import (
    helmet_presence_score,
    worst_helmet_presence_score,
)

_HELMET_DETS_CACHE: list[Detection] | None = None
_HELMET_DETS_IMAGE_ID: int | None = None


@dataclass
class HelmetAssessment:
    presence_score: float
    method: str  # yolo | heuristic | hybrid
    head_rois: list[list[float]]
    worst_head_roi: list[float]


def _image_token(image: np.ndarray) -> int:
    return id(image)


def get_helmet_yolo_detections(image: np.ndarray, refresh: bool = False) -> list[Detection]:
    """Cache per-frame helmet YOLO detections to avoid duplicate inference."""
    global _HELMET_DETS_CACHE, _HELMET_DETS_IMAGE_ID
    token = _image_token(image)
    if not refresh and _HELMET_DETS_CACHE is not None and _HELMET_DETS_IMAGE_ID == token:
        return _HELMET_DETS_CACHE
    if not helmet_model_available():
        _HELMET_DETS_CACHE = []
        _HELMET_DETS_IMAGE_ID = token
        return []
    _HELMET_DETS_CACHE = detect_helmet_objects(image)
    _HELMET_DETS_IMAGE_ID = token
    return _HELMET_DETS_CACHE


def clear_helmet_detection_cache() -> None:
    global _HELMET_DETS_CACHE, _HELMET_DETS_IMAGE_ID
    _HELMET_DETS_CACHE = None
    _HELMET_DETS_IMAGE_ID = None


def assess_rider_helmet(
    image: np.ndarray,
    person_bbox: list[float],
    image_shape: tuple[int, ...] | None = None,
    helmet_dets: list[Detection] | None = None,
) -> HelmetAssessment:
    """
    Assess helmet presence for a rider person box.
    Uses dedicated YOLO when available; falls back to heuristic on head ROIs.
    """
    shape = image_shape or image.shape
    rois = head_rois_from_person(person_bbox, shape)
    heuristic = worst_helmet_presence_score(image, person_bbox, shape)

    dets = helmet_dets if helmet_dets is not None else get_helmet_yolo_detections(image)
    yolo_score = yolo_worst_helmet_score_for_person(rois, dets) if dets else None

    if yolo_score is not None:
        # Hybrid: trust YOLO but never let heuristic bare-head signal be overridden upward
        combined = min(yolo_score, heuristic) if heuristic < 0.42 else yolo_score
        method = "hybrid" if combined != yolo_score else "yolo"
        score = combined
    else:
        score = heuristic
        method = "heuristic"

    worst_roi = min(rois, key=lambda r: helmet_presence_score(image, r))
    if yolo_score is not None and dets:
        from services.detection.helmet_yolo import yolo_helmet_presence_score

        yolo_per_roi = [(r, yolo_helmet_presence_score(r, dets)) for r in rois]
        matched = [r for r, s in yolo_per_roi if s is not None]
        if matched:
            worst_roi = min(
                matched,
                key=lambda r: yolo_helmet_presence_score(r, dets) or 1.0,
            )

    return HelmetAssessment(
        presence_score=score,
        method=method,
        head_rois=rois,
        worst_head_roi=worst_roi,
    )


def helmet_detected_from_score(score: float, threshold: float = 0.50) -> bool:
    return score >= threshold
