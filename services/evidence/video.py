"""Annotated demo video export — per-frame violation overlays like live CCTV review."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from config import EVIDENCE_DIR
from schemas import Detection
from services.evidence.service import COMPLIANT_COLOR, VIOLATION_COLOR, _draw_bbox

VEHICLE_CLASSES = {"motorcycle", "car", "bus", "truck", "bicycle"}


def _label_for_track(
    track_id: str,
    det: Detection,
    vehicle_labels: dict[str, str],
    violations_by_track: dict[str, list[str]],
) -> tuple[str, tuple[int, int, int]]:
    vid = vehicle_labels.get(track_id, "")
    types = violations_by_track.get(track_id, [])
    if types:
        short = ", ".join(t.replace("_", " ")[:18] for t in types[:2])
        label = f"{vid or det.class_name} | {short}" if vid else f"{det.class_name} | {short}"
        return label, VIOLATION_COLOR
    if vid:
        return f"{vid} | compliant", COMPLIANT_COLOR
    return det.class_name, COMPLIANT_COLOR


def render_annotated_frame(
    frame: np.ndarray,
    detections: list[Detection],
    vehicle_labels: dict[str, str],
    violations_by_track: dict[str, list[str]],
    frame_idx: int,
    total_frames: int,
    violation_count: int,
) -> np.ndarray:
    canvas = frame.copy()
    vehicles = [d for d in detections if d.class_name in VEHICLE_CLASSES]
    for det in vehicles:
        label, color = _label_for_track(det.track_id, det, vehicle_labels, violations_by_track)
        _draw_bbox(canvas, det.bbox, label, color)

    bar_h = 42
    cv2.rectangle(canvas, (0, 0), (canvas.shape[1], bar_h), (0, 0, 0), -1)
    header = (
        f"Nigha AI | frame {frame_idx + 1}/{total_frames} | "
        f"violations: {violation_count}"
    )
    cv2.putText(canvas, header, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)
    return canvas


def write_annotated_demo_video(
    frames: list[np.ndarray],
    tracked: list[list[Detection]],
    media_id: str,
    vehicle_labels: dict[str, str],
    violations_by_track: dict[str, list[str]],
    violation_count: int,
    fps: float = 6.0,
) -> str:
    """Write sampled annotated frames to MP4 for dashboard demo playback."""
    if not frames or not tracked:
        return ""

    out_path = EVIDENCE_DIR / f"{media_id}_enforcement.mp4"
    h, w = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h))
    if not writer.isOpened():
        return ""

    total = len(frames)
    for idx, (frame, dets) in enumerate(zip(frames, tracked)):
        annotated = render_annotated_frame(
            frame,
            dets,
            vehicle_labels,
            violations_by_track,
            idx,
            total,
            violation_count,
        )
        writer.write(annotated)
    writer.release()
    return str(out_path)
