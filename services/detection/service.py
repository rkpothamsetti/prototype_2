"""YOLO-based detection service."""
from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Optional

import cv2
import numpy as np

from config import settings
from schemas import Detection
from services.detection.demo_fallback import demo_contour_detection

YOLO_CLASS_MAP = {
    "car": "car",
    "motorcycle": "motorcycle",
    "bus": "bus",
    "truck": "truck",
    "person": "person",
    "bicycle": "bicycle",
}


@lru_cache(maxsize=1)
def _load_model():
    from ultralytics import YOLO

    return YOLO(settings.yolo_model)


def _is_likely_synthetic(image: np.ndarray) -> bool:
    """Uniform gray background → our OpenCV-generated demo samples."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    patches = [
        gray[0:40, 0:40],
        gray[0:40, w - 40 : w],
        gray[h - 40 : h, 0:40],
        gray[h - 40 : h, w - 40 : w],
    ]
    return all(float(np.std(p)) < 18.0 for p in patches)


def detect_objects(image: np.ndarray, conf: Optional[float] = None) -> list[Detection]:
    if settings.demo_fallback and _is_likely_synthetic(image):
        return _tag_drivers(demo_contour_detection(image))

    model = _load_model()
    threshold = conf if conf is not None else settings.yolo_confidence
    results = model.predict(image, conf=threshold, verbose=False)
    detections: list[Detection] = []

    if not results:
        return detections

    result = results[0]
    names = result.names
    boxes = result.boxes
    if boxes is None:
        return detections

    for box in boxes:
        cls_id = int(box.cls.item())
        class_name = names.get(cls_id, str(cls_id))
        mapped = YOLO_CLASS_MAP.get(class_name)
        if not mapped:
            continue
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        detections.append(
            Detection(
                track_id=str(uuid.uuid4()),
                class_name=mapped,
                bbox=[float(x1), float(y1), float(x2), float(y2)],
                confidence=float(box.conf.item()),
            )
        )

    detections = _tag_drivers(detections)

    if not detections and settings.demo_fallback:
        detections = _tag_drivers(demo_contour_detection(image))

    from services.association.engine import nms_detections

    return nms_detections(detections)


def _tag_drivers(detections: list[Detection]) -> list[Detection]:
    from services.common.utils import overlap_fraction

    vehicles = [d for d in detections if d.class_name in {"car", "truck", "bus"}]
    persons = [d for d in detections if d.class_name == "person"]

    for vehicle in vehicles:
        for person in persons:
            if overlap_fraction(person.bbox, vehicle.bbox) >= 0.4:
                person.role = "driver_candidate"
    return detections
