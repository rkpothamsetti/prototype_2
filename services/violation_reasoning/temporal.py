"""Temporal violation aggregation across video frames."""
from __future__ import annotations

from collections import defaultdict

import numpy as np

from schemas import Detection, PreprocessingMetadata, SceneConfig, ViolationRecord
from services.association.engine import VehicleRecord, build_scene_graph
from services.violation_reasoning.vehicle_eval import evaluate_all_vehicles

VEHICLE_CLASSES = {"motorcycle", "car", "bus", "truck", "bicycle"}
VIOLATION_FRAME_RATIO = 0.30


def evaluate_video_violations(
    raw_frames: list[np.ndarray],
    processed_frames: list[np.ndarray],
    tracked: list[list[Detection]],
    metadata: PreprocessingMetadata,
    scene: SceneConfig,
) -> tuple[list[ViolationRecord], list[VehicleRecord], list[Detection]]:
    """
    Run per-frame violation checks and keep violations seen in enough frames.
    Returns merged violations, vehicle records from the middle frame, and derived objects.
    """
    if not tracked or not processed_frames:
        return [], [], []

    mid = len(processed_frames) // 2
    type_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    sample_violation: dict[tuple[str, str], ViolationRecord] = {}
    derived: list[Detection] = []
    vehicles: list[VehicleRecord] = []

    for frame_idx, (raw, proc, dets) in enumerate(zip(raw_frames, processed_frames, tracked)):
        from services.violation_reasoning.helmet_eval import clear_helmet_detection_cache

        clear_helmet_detection_cache()
        frame_vehicles, frame_derived = build_scene_graph(proc, dets, scene, helmet_image=raw)
        if frame_idx == mid:
            vehicles = frame_vehicles
            derived = frame_derived
        frame_violations = evaluate_all_vehicles(
            proc,
            frame_vehicles,
            metadata,
            scene,
            frame_tracks=tracked,
            helmet_image=raw,
        )
        for v in frame_violations:
            key = (v.track_id, v.violation_type)
            type_counts[v.track_id][v.violation_type] += 1
            if key not in sample_violation:
                sample_violation[key] = v

    n_frames = max(len(tracked), 1)
    min_hits = max(1, int(n_frames * VIOLATION_FRAME_RATIO))
    merged: list[ViolationRecord] = []
    for (track_id, vtype), record in sample_violation.items():
        if type_counts[track_id][vtype] >= min_hits:
            merged.append(record)

    return merged, vehicles, derived


def violations_by_track(violations: list[ViolationRecord]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    for v in violations:
        if v.track_id and v.violation_type not in out[v.track_id]:
            out[v.track_id].append(v.violation_type)
    return dict(out)


def vehicle_labels_from_records(vehicles: list[VehicleRecord]) -> dict[str, str]:
    return {v.track_id: v.vehicle_id for v in vehicles}
