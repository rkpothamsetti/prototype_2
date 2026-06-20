"""Evidence and enforcement output tests."""
import numpy as np

from schemas import PreprocessingMetadata
from services.association.engine import VehicleRecord
from services.evidence.service import (
    build_enforcement_result,
    build_evidence_packages,
    load_enforcement_for_media,
    render_enforcement_image,
)
from schemas import ViolationRecord


def test_enforcement_image_colors(tmp_path, monkeypatch):
    monkeypatch.setattr("services.evidence.service.EVIDENCE_DIR", tmp_path)

    img = np.zeros((200, 300, 3), dtype=np.uint8)
    vehicle_ok = VehicleRecord(
        vehicle_id="VEH-001",
        vehicle_type="car",
        track_id="t1",
        bbox=[20, 80, 120, 180],
        confidence=0.9,
    )
    vehicle_bad = VehicleRecord(
        vehicle_id="VEH-002",
        vehicle_type="motorcycle",
        track_id="t2",
        bbox=[150, 80, 280, 180],
        confidence=0.9,
    )
    violations = [
        ViolationRecord(
            violation_type="triple_riding",
            confidence=0.9,
            reason="test",
            vehicle_id="VEH-002",
            track_id="t2",
            vehicle_class="motorcycle",
        )
    ]
    by_vehicle = {"VEH-002": violations}
    canvas = render_enforcement_image(img, [vehicle_ok, vehicle_bad], by_vehicle, "2026-01-01")
    assert canvas.shape == img.shape


def test_enforcement_json_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("services.evidence.service.EVIDENCE_DIR", tmp_path)

    img = np.zeros((100, 100, 3), dtype=np.uint8)
    meta = PreprocessingMetadata(
        quality_score=0.8,
        blur_variance=100,
        night_detected=False,
        original_size=[100, 100],
        processed_size=[100, 100],
    )
    vehicle = VehicleRecord(
        vehicle_id="VEH-001",
        vehicle_type="motorcycle",
        track_id="m1",
        bbox=[10, 10, 90, 90],
        confidence=0.9,
    )
    result, path = build_enforcement_result(
        media_id="roundtrip-media",
        job_id="job-rt",
        image=img,
        vehicles=[vehicle],
        violations=[],
        detections=[],
        derived=[],
        preprocessing=meta,
        plates_by_vehicle={},
        captured_at="2026-01-01T00:00:00Z",
    )
    loaded = load_enforcement_for_media("roundtrip-media")
    assert loaded is not None
    assert loaded.vehicles[0].vehicle_id == "VEH-001"
    assert loaded.job_id == "job-rt"
    assert path.endswith("_enforcement.jpg")


def test_evidence_packages_include_vehicle_id(preprocessing_meta):
    vehicle = VehicleRecord(
        vehicle_id="VEH-001",
        vehicle_type="motorcycle",
        track_id="m1",
        bbox=[10, 10, 90, 90],
        confidence=0.9,
    )
    violation = ViolationRecord(
        violation_type="triple_riding",
        confidence=0.9,
        reason="3 riders",
        vehicle_id="VEH-001",
        track_id="m1",
        vehicle_class="motorcycle",
    )
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    packages = build_evidence_packages(
        media_id="m1",
        image=img,
        vehicles=[vehicle],
        violations=[violation],
        preprocessing=preprocessing_meta,
        latitude=17.0,
        longitude=78.0,
        camera_id="CAM",
        captured_at="2026-01-01",
        plates_by_vehicle={},
        annotated_path="/tmp/x.jpg",
    )
    assert packages[0].vehicle["vehicle_id"] == "VEH-001"


def test_evidence_merged_per_vehicle(tmp_path, monkeypatch, preprocessing_meta):
    """Multiple violation types on one vehicle → single evidence package."""
    monkeypatch.setattr("services.evidence.service.EVIDENCE_DIR", tmp_path)

    vehicle = VehicleRecord(
        vehicle_id="VEH-001",
        vehicle_type="motorcycle",
        track_id="m1",
        bbox=[10, 10, 90, 90],
        confidence=0.9,
    )
    violations = [
        ViolationRecord(
            violation_type="triple_riding",
            confidence=0.9,
            reason="3 riders",
            vehicle_id="VEH-001",
            track_id="m1",
            vehicle_class="motorcycle",
            evidence_bboxes=[[10, 10, 90, 90]],
        ),
        ViolationRecord(
            violation_type="helmet_non_compliance",
            confidence=0.85,
            reason="No helmet",
            vehicle_id="VEH-001",
            track_id="m1",
            vehicle_class="motorcycle",
            evidence_bboxes=[[20, 20, 40, 40]],
        ),
    ]
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    packages = build_evidence_packages(
        media_id="m1",
        image=img,
        vehicles=[vehicle],
        violations=violations,
        preprocessing=preprocessing_meta,
        latitude=17.0,
        longitude=78.0,
        camera_id="CAM",
        captured_at="2026-01-01",
        plates_by_vehicle={},
        annotated_path="/tmp/x.jpg",
    )
    assert len(packages) == 1
    assert "triple_riding" in packages[0].violation["type"]
    assert "helmet_non_compliance" in packages[0].violation["type"]
    assert len(packages[0].violation["violations"]) == 2
    assert packages[0].annotated_path.endswith("_focus.jpg")
