"""Tests for association engine and per-vehicle enforcement."""
import numpy as np
import cv2

from schemas import Detection, SceneConfig
from services.association.engine import build_scene_graph, nms_detections
from services.violation_reasoning.service import evaluate_violations
from services.preprocessing.service import preprocess_image


def test_nms_removes_duplicate_boxes():
    dets = [
        Detection(track_id="a", class_name="car", bbox=[10, 10, 100, 100], confidence=0.9),
        Detection(track_id="b", class_name="car", bbox=[12, 12, 98, 98], confidence=0.8),
        Detection(track_id="c", class_name="person", bbox=[200, 200, 250, 300], confidence=0.7),
    ]
    kept = nms_detections(dets, iou_threshold=0.5)
    cars = [d for d in kept if d.class_name == "car"]
    assert len(cars) == 1


def test_vehicle_ids_assigned():
    image = np.zeros((400, 400, 3), dtype=np.uint8)
    detections = [
        Detection(track_id="m1", class_name="motorcycle", bbox=[50, 100, 200, 300], confidence=0.9),
        Detection(track_id="p1", class_name="person", bbox=[80, 50, 170, 200], confidence=0.85),
    ]
    vehicles, _ = build_scene_graph(image, detections, SceneConfig())
    assert len(vehicles) == 1
    assert vehicles[0].vehicle_id == "VEH-001"
    assert vehicles[0].rider_count >= 1


def test_inferred_motorcycle_from_person_only():
    image = np.zeros((400, 400, 3), dtype=np.uint8)
    detections = [
        Detection(track_id="p1", class_name="person", bbox=[100, 80, 200, 280], confidence=0.9),
    ]
    vehicles, _ = build_scene_graph(image, detections, SceneConfig())
    assert len(vehicles) == 1
    assert vehicles[0].vehicle_type == "motorcycle"
    assert vehicles[0].vehicle_id.startswith("VEH-")


def test_standing_bystanders_not_counted_as_riders():
    """Police / pedestrians beside a bike must not trigger triple riding."""
    image = np.zeros((600, 800, 3), dtype=np.uint8)
    detections = [
        Detection(track_id="bike", class_name="motorcycle", bbox=[300, 280, 520, 520], confidence=0.9),
        Detection(track_id="rider", class_name="person", bbox=[360, 180, 460, 400], confidence=0.88),
        # Standing officer to the left — feet on ground, beside bike
        Detection(track_id="cop1", class_name="person", bbox=[120, 120, 220, 520], confidence=0.85),
        Detection(track_id="cop2", class_name="person", bbox=[200, 130, 290, 530], confidence=0.84),
    ]
    vehicles, _ = build_scene_graph(image, detections, SceneConfig())
    bike = next(v for v in vehicles if v.vehicle_type == "motorcycle")
    assert bike.rider_count <= 1, f"expected 1 rider, got {bike.rider_count}"


def test_violations_linked_to_vehicle_id():
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.rectangle(image, (100, 200), (400, 450), (80, 80, 200), -1)
    for i in range(3):
        cx = 150 + i * 60
        cv2.circle(image, (cx, 120), 30, (180, 150, 130), -1)

    detections = [
        Detection(track_id="bike", class_name="motorcycle", bbox=[100, 150, 400, 450], confidence=0.9),
        Detection(track_id="r1", class_name="person", bbox=[120, 60, 180, 200], confidence=0.85),
        Detection(track_id="r2", class_name="person", bbox=[200, 60, 260, 200], confidence=0.85),
        Detection(track_id="r3", class_name="person", bbox=[280, 60, 340, 200], confidence=0.85),
    ]
    processed, meta, _ = preprocess_image(image, "triple-test")
    violations, vehicles, _ = evaluate_violations(processed, detections, meta, SceneConfig())
    assert vehicles
    for v in violations:
        assert v.vehicle_id, "every violation must have vehicle_id"
        assert v.vehicle_id.startswith("VEH-")
    types = {v.violation_type for v in violations}
    assert "triple_riding" in types


def test_child_on_bike_not_counted_in_triple_riding(blank_image, preprocessing_meta):
    """Small child on tank must not inflate triple-riding rider count."""
    from schemas import Detection, SceneConfig
    from services.association.engine import build_scene_graph
    from services.violation_reasoning.service import evaluate_violations

    image = blank_image.copy()
    detections = [
        Detection(track_id="bike", class_name="motorcycle", bbox=[300, 280, 520, 520], confidence=0.9),
        Detection(track_id="rider", class_name="person", bbox=[360, 180, 460, 400], confidence=0.88),
        Detection(track_id="pillion", class_name="person", bbox=[400, 200, 480, 380], confidence=0.86),
        Detection(track_id="child", class_name="person", bbox=[330, 320, 370, 400], confidence=0.80),
    ]
    vehicles, _ = build_scene_graph(image, detections, SceneConfig())
    bike = next(v for v in vehicles if v.vehicle_type == "motorcycle")
    assert bike.rider_count <= 2

    violations, _, _ = evaluate_violations(image, detections, preprocessing_meta, SceneConfig())
    triple = [v for v in violations if v.violation_type == "triple_riding"]
    assert not triple
