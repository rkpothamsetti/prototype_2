"""Tests for dedicated helmet YOLO integration."""
from pathlib import Path

import cv2
import numpy as np
import pytest

from services.detection.helmet_yolo import (
    detect_helmet_objects,
    helmet_model_available,
    resolve_helmet_model_path,
    yolo_helmet_presence_score,
)
from services.violation_reasoning.helmet_eval import assess_rider_helmet, clear_helmet_detection_cache


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_helmet_detection_cache()
    yield
    clear_helmet_detection_cache()


def test_helmet_model_path_resolution():
    path = resolve_helmet_model_path()
    if not Path("data/models/helmet_yolo.pt").exists():
        assert path is None or not path.is_file()
    else:
        assert path is not None and path.is_file()


@pytest.mark.skipif(not helmet_model_available(), reason="helmet YOLO weights not downloaded")
def test_helmet_yolo_detects_on_frame():
    """Dedicated YOLO should emit helmet / no_helmet boxes on real imagery."""
    img_path = Path(__file__).resolve().parents[1] / (
        "data/uploads/1439f008-34c5-405f-a53a-12dbbac0d92a.jpg"
    )
    if not img_path.exists():
        pytest.skip("VEH-002 test image missing")
    img = cv2.imread(str(img_path))
    dets = detect_helmet_objects(img)
    assert dets, "expected helmet YOLO detections on VEH-002 image"
    classes = {d.class_name for d in dets}
    assert "no_helmet" in classes or "helmet" in classes


@pytest.mark.skipif(not helmet_model_available(), reason="helmet YOLO weights not downloaded")
def test_veh002_yolo_assessment_no_helmet():
    """VEH-002 stacked riders: YOLO + hybrid should flag bare adult head."""
    from schemas import SceneConfig
    from services.detection.service import detect_objects
    from services.preprocessing.service import preprocess_frame
    from services.violation_reasoning.service import evaluate_violations

    img_path = Path(__file__).resolve().parents[1] / (
        "data/uploads/1439f008-34c5-405f-a53a-12dbbac0d92a.jpg"
    )
    if not img_path.exists():
        pytest.skip("VEH-002 test image missing")
    raw = cv2.imread(str(img_path))
    proc, meta = preprocess_frame(raw)
    viols, vehicles, _ = evaluate_violations(
        proc, detect_objects(proc), meta, SceneConfig(), source_image=raw
    )
    moto = next((v for v in vehicles if v.vehicle_id == "VEH-002"), None)
    assert moto is not None
    helmet_v = [
        v for v in viols
        if v.vehicle_id == "VEH-002" and v.violation_type == "helmet_non_compliance"
    ]
    assert helmet_v, "VEH-002 should remain helmet non-compliant with YOLO enabled"
    assert not moto.associated_persons[0].helmet_detected


def test_yolo_score_none_without_overlap():
    """No overlapping YOLO box → caller falls back to heuristic."""
    head = [10.0, 10.0, 50.0, 50.0]
    far = [
        __import__("schemas").Detection(
            track_id="HYOLO-1",
            class_name="no_helmet",
            bbox=[200.0, 200.0, 250.0, 250.0],
            confidence=0.9,
        )
    ]
    assert yolo_helmet_presence_score(head, far) is None


def test_assess_rider_helmet_heuristic_fallback():
    """Without model weights, heuristic path still works."""
    img = np.full((100, 80, 3), 200, dtype=np.uint8)
    cv2.ellipse(img, (40, 50), (25, 35), 0, 0, 360, (180, 150, 130), -1)
    assessment = assess_rider_helmet(img, [0.0, 0.0, 80.0, 100.0])
    if helmet_model_available():
        assert assessment.method in {"heuristic", "yolo", "hybrid"}
    else:
        assert assessment.method == "heuristic"
    assert assessment.presence_score < 0.42
