"""Dedicated YOLO helmet / no-helmet detector (ThanhSan-style second stage)."""
from __future__ import annotations

import uuid
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np

from config import ROOT_DIR, settings
from schemas import Detection
from services.common.utils import iou, overlap_fraction

MODELS_DIR = ROOT_DIR / "data" / "models"

HELMET_POSITIVE = {
    "helmet",
    "with_helmet",
    "with helmet",
    "helmet_on",
    "wearing_helmet",
    "helmeted",
}
HELMET_NEGATIVE = {
    "no_helmet",
    "no helmet",
    "no-helmet",
    "without_helmet",
    "head",
    "bare_head",
    "nohelmet",
}


def resolve_helmet_model_path() -> Path | None:
    """Return path to helmet YOLO weights if configured and present."""
    if not settings.use_helmet_yolo:
        return None
    raw = settings.helmet_yolo_model
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT_DIR / raw
    if path.is_file():
        return path
    fallback = MODELS_DIR / "helmet_yolo.pt"
    return fallback if fallback.is_file() else None


def helmet_model_available() -> bool:
    return resolve_helmet_model_path() is not None


@lru_cache(maxsize=1)
def _load_helmet_model():
    path = resolve_helmet_model_path()
    if path is None:
        return None
    from ultralytics import YOLO

    return YOLO(str(path))


def _normalize_class(name: str) -> str:
    return name.lower().replace("-", "_").replace(" ", "_").strip()


def _class_polarity(class_name: str) -> str | None:
    norm = _normalize_class(class_name)
    if norm in {_normalize_class(c) for c in HELMET_POSITIVE}:
        return "helmet"
    if norm in {_normalize_class(c) for c in HELMET_NEGATIVE}:
        return "no_helmet"
    if "no" in norm and "helmet" in norm:
        return "no_helmet"
    if "helmet" in norm:
        return "helmet"
    return None


def detect_helmet_objects(
    image: np.ndarray,
    conf: Optional[float] = None,
) -> list[Detection]:
    """Run dedicated helmet YOLO on full frame."""
    model = _load_helmet_model()
    if model is None:
        return []

    threshold = conf if conf is not None else settings.helmet_yolo_confidence
    results = model.predict(image, conf=threshold, verbose=False)
    if not results:
        return []

    result = results[0]
    boxes = result.boxes
    names = result.names
    if boxes is None:
        return []

    out: list[Detection] = []
    for box in boxes:
        cls_id = int(box.cls.item())
        raw_name = names.get(cls_id, str(cls_id))
        polarity = _class_polarity(str(raw_name))
        if polarity is None:
            continue
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        out.append(
            Detection(
                track_id=f"HYOLO-{uuid.uuid4().hex[:8]}",
                class_name=polarity,
                bbox=[float(x1), float(y1), float(x2), float(y2)],
                confidence=float(box.conf.item()),
                role=f"helmet_yolo:{raw_name}",
            )
        )
    return out


def _intersect_bbox(a: list[float], b: list[float]) -> list[float]:
    return [max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])]


def _head_overlap(head_bbox: list[float], det_bbox: list[float]) -> tuple[float, float]:
    inter = _intersect_bbox(head_bbox, det_bbox)
    if inter[0] >= inter[2] or inter[1] >= inter[3]:
        return 0.0, 0.0
    return iou(head_bbox, det_bbox), overlap_fraction(inter, head_bbox)


def yolo_helmet_presence_score(
    head_bbox: list[float],
    helmet_dets: list[Detection],
    min_overlap: float = 0.12,
) -> float | None:
    """
    Helmet presence 0–1 from YOLO boxes overlapping a head ROI.
    Returns None when no YOLO hit overlaps the head (caller should use heuristic).
    """
    best_helmet = 0.0
    best_no = 0.0
    for det in helmet_dets:
        iou_val, ov = _head_overlap(head_bbox, det.bbox)
        if max(iou_val, ov) < min_overlap:
            continue
        weight = max(iou_val, ov) * det.confidence
        if det.class_name == "helmet":
            best_helmet = max(best_helmet, weight)
        elif det.class_name == "no_helmet":
            best_no = max(best_no, weight)

    if best_helmet <= 0 and best_no <= 0:
        return None
    if best_no > best_helmet:
        return float(max(0.0, 1.0 - best_no))
    return float(min(1.0, best_helmet))


def yolo_worst_helmet_score_for_person(
    head_rois: list[list[float]],
    helmet_dets: list[Detection],
) -> float | None:
    """Minimum YOLO-based helmet score across head bands; None if no YOLO coverage."""
    scores: list[float] = []
    for roi in head_rois:
        s = yolo_helmet_presence_score(roi, helmet_dets)
        if s is not None:
            scores.append(s)
    if not scores:
        return None
    return min(scores)
