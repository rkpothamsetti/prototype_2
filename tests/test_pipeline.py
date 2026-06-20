"""End-to-end pipeline integration tests (mocked detection for speed)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import cv2
import numpy as np
import pytest

from db.models import Evidence, Media, ProcessingJob
from schemas import Detection, PlateResult, SceneConfig
from services.pipeline import process_media_job


def _synthetic_detections(violation: str) -> list[Detection]:
  if violation == "triple_riding":
    return [
      Detection(track_id="m1", class_name="motorcycle", bbox=[100, 150, 400, 450], confidence=0.9),
      Detection(track_id="r1", class_name="person", bbox=[120, 60, 180, 200], confidence=0.85),
      Detection(track_id="r2", class_name="person", bbox=[200, 60, 260, 200], confidence=0.85),
      Detection(track_id="r3", class_name="person", bbox=[280, 60, 340, 200], confidence=0.85),
    ]
  if violation == "illegal_parking":
    return [Detection(track_id="c1", class_name="car", bbox=[150, 320, 350, 420], confidence=0.88)]
  return [
    Detection(track_id="m1", class_name="motorcycle", bbox=[100, 150, 400, 450], confidence=0.9),
    Detection(track_id="r1", class_name="person", bbox=[150, 50, 220, 200], confidence=0.85),
  ]


@pytest.mark.parametrize("violation_type", ["triple_riding", "illegal_parking", "compliant"])
def test_pipeline_produces_enforcement(db_session, tmp_path, violation_type):
    img = np.full((480, 640, 3), 200, dtype=np.uint8)
    if violation_type == "illegal_parking":
        cv2.rectangle(img, (150, 320), (350, 420), (100, 100, 200), -1)
    else:
        cv2.rectangle(img, (100, 150), (400, 450), (80, 80, 200), -1)

    image_path = tmp_path / "uploads" / "media-test.jpg"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(image_path), img)

    media_id = f"media-{uuid.uuid4().hex[:8]}"
    job_id = f"job-{media_id[:8]}"
    media = Media(
        media_id=media_id,
        filename="test.jpg",
        media_type="image",
        stored_path=str(image_path),
        captured_at=datetime.now(timezone.utc).isoformat(),
        latitude=17.38,
        longitude=78.48,
        camera_id="CAM_TEST",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    job = ProcessingJob(
        job_id=job_id,
        media_id=media_id,
        status="queued",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db_session.add(media)
    db_session.add(job)
    db_session.commit()

    scene = SceneConfig(
        no_parking_zones=[[100, 300, 500, 600]] if violation_type == "illegal_parking" else [],
    )
    mock_dets = _synthetic_detections(violation_type)
    empty_plate = PlateResult()

    with (
        patch("services.pipeline.detect_objects", return_value=mock_dets),
        patch("services.pipeline.extract_plate_from_vehicle", return_value=empty_plate),
        patch("services.pipeline.find_plates_in_image", return_value=[]),
    ):
        result = process_media_job(db_session, media, scene_config=scene, job_id=job_id)

    assert result.status == "completed", result.error_message
    assert result.enforcement is not None
    assert len(result.enforcement.vehicles) >= 1
    assert result.annotated_path
    assert (tmp_path / "evidence" / f"{media_id}_enforcement.json").exists()

    evidence_rows = db_session.query(Evidence).filter(Evidence.job_id == job_id).all()
    assert evidence_rows
    for row in evidence_rows:
        if row.violation_type != "none":
            assert row.vehicle_id or row.track_id

    if violation_type == "triple_riding":
        types = [v.violation["type"] for v in result.evidence if v.violation["type"] != "none"]
        assert any("triple_riding" in t for t in types)
    elif violation_type == "illegal_parking":
        types = [v.violation["type"] for v in result.evidence]
        assert any("illegal_parking" in t for t in types)


def test_pipeline_failed_job_sets_error(db_session, tmp_path):
    media_id = f"fail-{uuid.uuid4().hex[:8]}"
    job_id = f"job-{uuid.uuid4().hex[:8]}"
    media = Media(
        media_id=media_id,
        filename="missing.jpg",
        media_type="image",
        stored_path=str(tmp_path / "nonexistent.jpg"),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    job = ProcessingJob(job_id=job_id, media_id=media_id, status="queued", created_at=datetime.now(timezone.utc).isoformat())
    db_session.add(media)
    db_session.add(job)
    db_session.commit()

    result = process_media_job(db_session, media, job_id=job_id)
    assert result.status == "failed"
    assert result.error_message
