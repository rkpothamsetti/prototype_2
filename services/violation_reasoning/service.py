"""Violation reasoning engine — per-vehicle enforcement only."""
from __future__ import annotations

from typing import Optional

import numpy as np

from schemas import Detection, PreprocessingMetadata, SceneConfig, ViolationRecord
from services.association.engine import VehicleRecord, build_scene_graph
from services.violation_reasoning.vehicle_eval import evaluate_all_vehicles


def evaluate_violations(
    image: np.ndarray,
    detections: list[Detection],
    metadata: PreprocessingMetadata,
    scene: Optional[SceneConfig] = None,
    frame_tracks: Optional[list[list[Detection]]] = None,
    source_image: Optional[np.ndarray] = None,
) -> tuple[list[ViolationRecord], list[VehicleRecord], list[Detection]]:
    """
    Evaluate violations for every vehicle in the scene.
    Returns (violations, vehicle_records, derived_detections).
    Every violation is linked to vehicle_id — never global.
    """
    scene = scene or SceneConfig()
    helmet_image = source_image if source_image is not None else image
    vehicles, derived = build_scene_graph(image, detections, scene, helmet_image=helmet_image)
    violations = evaluate_all_vehicles(
        image, vehicles, metadata, scene, frame_tracks, helmet_image=helmet_image
    )
    return _dedupe_violations(violations), vehicles, derived


def _dedupe_violations(violations: list[ViolationRecord]) -> list[ViolationRecord]:
    seen: set[tuple[str, str]] = set()
    unique: list[ViolationRecord] = []
    for v in violations:
        key = (v.violation_type, v.vehicle_id or v.track_id)
        if key in seen:
            continue
        seen.add(key)
        unique.append(v)
    return unique
