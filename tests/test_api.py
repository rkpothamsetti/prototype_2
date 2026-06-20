"""API endpoint tests."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from db.models import Evidence, Media, ProcessingJob
from schemas import EnforcementResult, VehicleEnforcementRecord


@pytest.fixture
def api_client(db_session, monkeypatch):
    monkeypatch.setattr("config.settings.warmup_enabled", False)
    from db.database import get_db
    from api.main import app

    def override_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_health(api_client):
    res = api_client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["app"] == "Nigha AI"
    assert "per_vehicle_enforcement" in data["features"]
    assert "models_ready" in data
    assert "models_loaded" in data


def test_get_job_returns_enforcement(api_client, db_session, tmp_path, monkeypatch):
    from services.evidence.service import build_enforcement_result
    from schemas import PreprocessingMetadata
    import numpy as np

    media_id = f"api-{uuid.uuid4().hex[:8]}"
    job_id = f"job-{uuid.uuid4().hex[:8]}"
    ev_id = str(uuid.uuid4())
    db_session.add(
        Media(
            media_id=media_id,
            filename="t.jpg",
            media_type="image",
            stored_path="/tmp/t.jpg",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    )
    db_session.add(
        ProcessingJob(
            job_id=job_id,
            media_id=media_id,
            status="completed",
            latency_ms=1200.0,
            created_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
    )
    db_session.add(
        Evidence(
            evidence_id=ev_id,
            media_id=media_id,
            job_id=job_id,
            violation_type="triple_riding",
            confidence=0.9,
            reason="test",
            vehicle_class="motorcycle",
            track_id="m1",
            vehicle_id="VEH-001",
            annotated_path="/tmp/test.jpg",
            review_status="pending_review",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    )
    db_session.commit()

    img = np.zeros((100, 100, 3), dtype=np.uint8)
    meta = PreprocessingMetadata(
        quality_score=0.8,
        blur_variance=100,
        night_detected=False,
        original_size=[100, 100],
        processed_size=[100, 100],
    )
    from services.association.engine import VehicleRecord

    vehicle = VehicleRecord(
        vehicle_id="VEH-001",
        vehicle_type="motorcycle",
        track_id="m1",
        bbox=[10, 10, 90, 90],
        confidence=0.9,
        rider_count=3,
    )
    build_enforcement_result(
        media_id=media_id,
        job_id=job_id,
        image=img,
        vehicles=[vehicle],
        violations=[],
        detections=[],
        derived=[],
        preprocessing=meta,
        plates_by_vehicle={},
        captured_at=datetime.now(timezone.utc).isoformat(),
    )

    res = api_client.get(f"/api/v1/jobs/{job_id}")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "completed"
    assert body["enforcement"] is not None
    assert body["enforcement"]["vehicles"][0]["vehicle_id"] == "VEH-001"
    assert body["evidence"][0]["vehicle"]["vehicle_id"] == "VEH-001"


def test_evidence_ignores_undefined_filter(api_client, db_session):
    db_session.add(
        Evidence(
            evidence_id=str(uuid.uuid4()),
            media_id="m2",
            job_id="j2",
            violation_type="helmet_non_compliance",
            confidence=0.8,
            reason="test",
            review_status="pending_review",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    )
    db_session.commit()

    res = api_client.get("/api/v1/evidence?violation_type=undefined&plate=undefined")
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_review_update(api_client, db_session):
    ev_id = str(uuid.uuid4())
    db_session.add(
        Evidence(
            evidence_id=ev_id,
            media_id="m3",
            job_id="j3",
            violation_type="triple_riding",
            confidence=0.9,
            reason="test",
            review_status="pending_review",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    )
    db_session.commit()

    res = api_client.patch(f"/api/v1/evidence/{ev_id}/review?review_status=confirmed")
    assert res.status_code == 200
    assert res.json()["review_status"] == "confirmed"
