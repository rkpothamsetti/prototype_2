"""Per-violation-type unit tests — all rules tied to vehicle_id."""
import numpy as np

from schemas import SceneConfig
from services.association.engine import AssociatedPerson, build_scene_graph
from services.violation_reasoning.service import evaluate_violations
from services.violation_reasoning.vehicle_eval import evaluate_vehicle_violations
from helpers import make_vehicle_record


def test_triple_riding_violation(blank_image, preprocessing_meta, motorcycle_with_riders_detections):
    violations, vehicles, _ = evaluate_violations(
        blank_image, motorcycle_with_riders_detections, preprocessing_meta, SceneConfig()
    )
    assert any(v.violation_type == "triple_riding" for v in violations)
    for v in violations:
        assert v.vehicle_id.startswith("VEH-")


def test_illegal_parking_violation(blank_image, preprocessing_meta, car_in_zone_detections):
    scene = SceneConfig(no_parking_zones=[[100, 300, 500, 600]])
    violations, _, _ = evaluate_violations(blank_image, car_in_zone_detections, preprocessing_meta, scene)
    assert any(v.violation_type == "illegal_parking" for v in violations)


def test_stop_line_violation(blank_image, preprocessing_meta, car_in_zone_detections):
    scene = SceneConfig(stop_line_y=350.0, signal_state="red")
    violations, _, _ = evaluate_violations(blank_image, car_in_zone_detections, preprocessing_meta, scene)
    assert any(v.violation_type == "stop_line_violation" for v in violations)


def test_red_light_violation(blank_image, preprocessing_meta, car_in_zone_detections):
    scene = SceneConfig(
        traffic_light_state="red",
        intersection_roi=[100, 250, 500, 500],
    )
    violations, _, _ = evaluate_violations(blank_image, car_in_zone_detections, preprocessing_meta, scene)
    assert any(v.violation_type == "red_light_violation" for v in violations)


def test_wrong_side_driving(blank_image, preprocessing_meta):
    from schemas import Detection

    # Wide horizontal bbox → ~0° orientation; legal flow at 180° → violation
    detections = [
        Detection(track_id="c1", class_name="car", bbox=[50, 220, 450, 280], confidence=0.9),
    ]
    scene = SceneConfig(legal_direction_angle=180.0)
    violations, _, _ = evaluate_violations(blank_image, detections, preprocessing_meta, scene)
    assert any(v.violation_type == "wrong_side_driving" for v in violations)


def test_no_global_violations_without_vehicle(blank_image, preprocessing_meta):
    from schemas import Detection

    detections = [Detection(track_id="p1", class_name="person", bbox=[100, 80, 200, 280], confidence=0.9)]
    violations, vehicles, _ = evaluate_violations(blank_image, detections, preprocessing_meta, SceneConfig())
    # Person-only → inferred motorcycle vehicle; violations still have vehicle_id
    assert len(vehicles) == 1
    for v in violations:
        assert v.vehicle_id


def test_compliant_motorcycle_no_violations(blank_image, preprocessing_meta):
    from schemas import Detection

    detections = [
        Detection(track_id="m1", class_name="motorcycle", bbox=[100, 150, 400, 450], confidence=0.9),
        Detection(track_id="r1", class_name="person", bbox=[150, 50, 220, 200], confidence=0.85),
    ]
    # Add dark helmet shell on head region
    img = blank_image.copy()
    import cv2

    cv2.rectangle(img, (150, 50), (220, 100), (25, 25, 25), -1)
    violations, vehicles, _ = evaluate_violations(img, detections, preprocessing_meta, SceneConfig())
    triple = [v for v in violations if v.violation_type == "triple_riding"]
    assert not triple
    assert vehicles[0].vehicle_id == "VEH-001"


def test_seatbelt_violation_on_car(blank_image, preprocessing_meta, car_with_driver_detections):
    vehicle = make_vehicle_record(vehicle_type="car", riders=0)
    vehicle.associated_persons = [
        AssociatedPerson(
            person_id="d1",
            bbox=[180, 220, 280, 400],
            confidence=0.85,
            role="driver",
            proximity_score=0.9,
        )
    ]
    violations = evaluate_vehicle_violations(blank_image, vehicle, preprocessing_meta, SceneConfig())
    assert any(v.violation_type == "seatbelt_non_compliance" for v in violations)
    assert violations[0].vehicle_id == "VEH-001"


def test_multiple_violations_same_vehicle(blank_image, preprocessing_meta):
    from schemas import Detection

    detections = [
        Detection(track_id="m1", class_name="motorcycle", bbox=[100, 150, 400, 450], confidence=0.9),
        Detection(track_id="r1", class_name="person", bbox=[120, 60, 180, 200], confidence=0.85),
        Detection(track_id="r2", class_name="person", bbox=[200, 60, 260, 200], confidence=0.85),
        Detection(track_id="r3", class_name="person", bbox=[280, 60, 340, 200], confidence=0.85),
    ]
    scene = SceneConfig(stop_line_y=400.0, signal_state="red")
    violations, _, _ = evaluate_violations(blank_image, detections, preprocessing_meta, scene)
    types = {v.violation_type for v in violations}
    assert "triple_riding" in types
    assert "stop_line_violation" in types
    vehicle_ids = {v.vehicle_id for v in violations}
    assert len(vehicle_ids) == 1


def test_helmet_associated_to_rider(blank_image, preprocessing_meta):
    from schemas import Detection
    import cv2

    img = blank_image.copy()
    cv2.rectangle(img, (150, 40), (220, 95), (20, 20, 20), -1)
    detections = [
        Detection(track_id="m1", class_name="motorcycle", bbox=[100, 150, 400, 450], confidence=0.9),
        Detection(track_id="r1", class_name="person", bbox=[150, 50, 220, 200], confidence=0.85),
    ]
    vehicles, derived = build_scene_graph(img, detections, SceneConfig())
    helmets = [d for d in derived if d.class_name == "helmet"]
    assert vehicles[0].associated_persons[0].helmet_detected or helmets
