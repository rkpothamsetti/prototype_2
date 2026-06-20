"""Tests for annotated video demo export."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import cv2
import numpy as np
import pytest

from db.models import Media, ProcessingJob
from schemas import Detection, PlateResult, SceneConfig
from services.evidence.video import render_annotated_frame, write_annotated_demo_video
from services.pipeline import process_media_job


def test_render_annotated_frame_labels_violation():
    frame = np.full((240, 320, 3), 180, dtype=np.uint8)
    dets = [
        Detection(track_id="t1", class_name="motorcycle", bbox=[40, 80, 200, 220], confidence=0.9),
    ]
    out = render_annotated_frame(
        frame,
        dets,
        {"t1": "VEH-001"},
        {"t1": ["helmet_non_compliance"]},
        0,
        5,
        1,
    )
    assert out.shape == frame.shape


def test_write_annotated_demo_video(tmp_path, monkeypatch):
    from config import EVIDENCE_DIR

    monkeypatch.setattr("services.evidence.video.EVIDENCE_DIR", tmp_path)
    frames = [np.full((120, 160, 3), 200, dtype=np.uint8) for _ in range(3)]
    tracked = [
        [Detection(track_id="t1", class_name="motorcycle", bbox=[20, 40, 120, 100], confidence=0.9)]
        for _ in range(3)
    ]
    path = write_annotated_demo_video(
        frames,
        tracked,
        "demo-media",
        {"t1": "VEH-001"},
        {"t1": ["helmet_non_compliance"]},
        1,
    )
    assert path
    assert (tmp_path / "demo-media_enforcement.mp4").exists()


def test_video_pipeline_writes_mp4(db_session, tmp_path, monkeypatch):
    from config import EVIDENCE_DIR, UPLOAD_DIR

    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "uploads").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("config.EVIDENCE_DIR", evidence_dir)
    monkeypatch.setattr("services.evidence.service.EVIDENCE_DIR", evidence_dir)
    monkeypatch.setattr("services.evidence.video.EVIDENCE_DIR", evidence_dir)

    video_path = tmp_path / "uploads" / "clip.mp4"
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        10,
        (320, 240),
    )
    for _ in range(10):
        frame = np.full((240, 320, 3), 190, dtype=np.uint8)
        cv2.rectangle(frame, (80, 60), (220, 200), (60, 60, 180), -1)
        writer.write(frame)
    writer.release()

    media_id = f"vid-{uuid.uuid4().hex[:8]}"
    job_id = f"job-{media_id[:8]}"
    media = Media(
        media_id=media_id,
        filename="clip.mp4",
        media_type="video",
        stored_path=str(video_path),
        captured_at=datetime.now(timezone.utc).isoformat(),
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

    mock_dets = [
        Detection(track_id="m1", class_name="motorcycle", bbox=[80, 60, 220, 200], confidence=0.9),
        Detection(track_id="r1", class_name="person", bbox=[110, 20, 180, 120], confidence=0.85),
    ]
    empty_plate = PlateResult()

    with (
        patch("services.pipeline.detect_objects", return_value=mock_dets),
        patch("services.pipeline.extract_plate_from_vehicle", return_value=empty_plate),
        patch("services.pipeline.find_plates_in_image", return_value=[]),
    ):
        result = process_media_job(db_session, media, scene_config=SceneConfig(), job_id=job_id)

    assert result.status == "completed", result.error_message
    assert result.annotated_video_path
    assert (evidence_dir / f"{media_id}_enforcement.mp4").exists()


def test_extract_video_frames_spreads_across_clip(tmp_path):
    from services.pipeline import _extract_video_frames

    video_path = tmp_path / "long.mp4"
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        10,
        (160, 120),
    )
    for i in range(100):
        frame = np.full((120, 160, 3), i, dtype=np.uint8)
        writer.write(frame)
    writer.release()

    frames = _extract_video_frames(video_path, max_frames=5)
    assert len(frames) == 5
    # First frame should not be the only sample — later frames differ in pixel value
    assert frames[0].mean() < frames[-1].mean()
