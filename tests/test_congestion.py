"""Tests for congestion classification."""
from schemas import Detection
from services.congestion.classifier import classify_congestion


def test_congestion_free_flow():
    result = classify_congestion([], image_shape=(480, 640, 3))
    assert result.congestion_level == "free_flow"
    assert result.vehicle_count == 0


def test_congestion_gridlock_many_vehicles():
    dets = [
        Detection(track_id=f"v{i}", class_name="car", bbox=[10 + i * 5, 10, 60 + i * 5, 60], confidence=0.9)
        for i in range(30)
    ]
    result = classify_congestion(dets, image_shape=(480, 640, 3))
    assert result.congestion_level in {"heavy", "gridlock"}
    assert result.vehicle_count == 30


def test_congestion_moderate():
    dets = [
        Detection(track_id="v1", class_name="car", bbox=[100, 100, 200, 200], confidence=0.9),
        Detection(track_id="v2", class_name="motorcycle", bbox=[300, 100, 380, 200], confidence=0.9),
    ]
    result = classify_congestion(dets, image_shape=(480, 640, 3))
    assert result.congestion_level in {"free_flow", "moderate", "heavy"}
