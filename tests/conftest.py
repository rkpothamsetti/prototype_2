"""Shared pytest fixtures."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import pytest

# Keep test startup fast — full warmup runs only in production / eval scripts
os.environ.setdefault("TV_WARMUP_ENABLED", "false")

from schemas import Detection, PreprocessingMetadata, SceneConfig


@pytest.fixture
def blank_image() -> np.ndarray:
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def preprocessing_meta() -> PreprocessingMetadata:
    return PreprocessingMetadata(
        quality_score=0.85,
        blur_variance=120.0,
        night_detected=False,
        enhancements_applied=[],
        original_size=[640, 480],
        processed_size=[640, 480],
    )


@pytest.fixture
def motorcycle_with_riders_detections() -> list[Detection]:
    return [
        Detection(track_id="m1", class_name="motorcycle", bbox=[100, 150, 400, 450], confidence=0.9),
        Detection(track_id="r1", class_name="person", bbox=[120, 60, 180, 200], confidence=0.85),
        Detection(track_id="r2", class_name="person", bbox=[200, 60, 260, 200], confidence=0.85),
        Detection(track_id="r3", class_name="person", bbox=[280, 60, 340, 200], confidence=0.85),
    ]


@pytest.fixture
def car_in_zone_detections() -> list[Detection]:
    return [
        Detection(track_id="c1", class_name="car", bbox=[150, 320, 350, 420], confidence=0.88),
    ]


@pytest.fixture
def car_with_driver_detections() -> list[Detection]:
    return [
        Detection(
            track_id="c1",
            class_name="car",
            bbox=[100, 200, 400, 450],
            confidence=0.9,
        ),
        Detection(
            track_id="d1",
            class_name="person",
            bbox=[180, 220, 280, 400],
            confidence=0.85,
            role="driver_candidate",
        ),
    ]


@pytest.fixture
def write_test_image(tmp_path: Path):
    def _write(name: str = "test.jpg") -> Path:
        img = np.full((480, 640, 3), 200, dtype=np.uint8)
        cv2.rectangle(img, (100, 200), (400, 450), (80, 80, 200), -1)
        path = tmp_path / name
        cv2.imwrite(str(path), img)
        return path

    return _write


@pytest.fixture
def db_session(tmp_path, monkeypatch):
    """Isolated SQLite session — does not touch production trafficvision.db."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from db import models  # noqa: F401
    from db.database import Base, _migrate_columns

    db_path = tmp_path / "test.db"
    evidence_dir = tmp_path / "evidence"
    upload_dir = tmp_path / "uploads"
    processed_dir = tmp_path / "processed"
    for d in (evidence_dir, upload_dir, processed_dir):
        d.mkdir(parents=True)

    test_engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    TestSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=test_engine)
    _migrate_columns(test_engine)

    monkeypatch.setattr("db.database.engine", test_engine)
    monkeypatch.setattr("db.database.SessionLocal", TestSession)
    monkeypatch.setattr("config.EVIDENCE_DIR", evidence_dir)
    monkeypatch.setattr("config.UPLOAD_DIR", upload_dir)
    monkeypatch.setattr("config.PROCESSED_DIR", processed_dir)
    monkeypatch.setattr("services.evidence.service.EVIDENCE_DIR", evidence_dir)
    monkeypatch.setattr("services.preprocessing.service.PROCESSED_DIR", processed_dir)

    db = TestSession()
    yield db
    db.close()
