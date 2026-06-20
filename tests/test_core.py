"""Unit tests for TrafficVision core utilities and rules."""
import numpy as np

from services.common.utils import (
    iou,
    normalize_indian_plate,
    point_in_rect,
    validate_indian_plate,
)
from services.violation_reasoning.service import _dedupe_violations
from schemas import ViolationRecord


def test_iou_full_overlap():
    assert iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0


def test_iou_no_overlap():
    assert iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0


def test_indian_plate_normalization():
    assert normalize_indian_plate("ap 09 ab 1234") == "AP09AB1234"


def test_indian_plate_validation():
    pattern = r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$"
    assert validate_indian_plate("AP09AB1234", pattern)
    assert not validate_indian_plate("INVALID", pattern)


def test_point_in_rect():
    assert point_in_rect(5, 5, [0, 0, 10, 10])
    assert not point_in_rect(15, 5, [0, 0, 10, 10])


def test_dedupe_violations():
    v1 = ViolationRecord(
        violation_type="triple_riding",
        confidence=0.9,
        reason="test",
        track_id="a",
    )
    v2 = ViolationRecord(
        violation_type="triple_riding",
        confidence=0.8,
        reason="test2",
        track_id="a",
    )
    result = _dedupe_violations([v1, v2])
    assert len(result) == 1


def test_preprocessing_quality():
    from services.preprocessing.service import preprocess_image
    import cv2

    image = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.rectangle(image, (100, 100), (500, 400), (255, 255, 255), -1)
    processed, meta, path = preprocess_image(image, "test-media")
    assert meta.processed_size[0] <= 640
    assert path.exists()
