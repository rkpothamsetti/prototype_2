"""Evidence generation and per-vehicle enforcement annotation."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np

from config import EVIDENCE_DIR
from schemas import (
    AssociatedPersonOut,
    CongestionResult,
    Detection,
    EnforcementResult,
    EvidencePackage,
    PlateResult,
    PreprocessingMetadata,
    VehicleEnforcementRecord,
    ViolationRecord,
)
from services.association.engine import VehicleRecord

COMPLIANT_COLOR = (0, 200, 0)
VIOLATION_COLOR = (0, 0, 255)


def _draw_bbox(image: np.ndarray, bbox: list[float], label: str, color: tuple[int, int, int]) -> None:
    x1, y1, x2, y2 = [int(v) for v in bbox]
    cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
    cv2.putText(image, label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)


def render_enforcement_image(
    image: np.ndarray,
    vehicles: list[VehicleRecord],
    violations_by_vehicle: dict[str, list[ViolationRecord]],
    timestamp: str,
) -> np.ndarray:
    """Green box = compliant vehicle, Red box = violation; label shows VEH-ID + types."""
    canvas = image.copy()

    for vehicle in vehicles:
        v_violations = violations_by_vehicle.get(vehicle.vehicle_id, [])
        has_violation = len(v_violations) > 0
        color = VIOLATION_COLOR if has_violation else COMPLIANT_COLOR
        if has_violation:
            types = ", ".join(v.violation_type for v in v_violations[:3])
            if len(v_violations) > 3:
                types += "..."
            label = f"{vehicle.vehicle_id} | {types}"
        else:
            label = f"{vehicle.vehicle_id} | compliant"
        _draw_bbox(canvas, vehicle.bbox, label, color)

    overlay = f"Nigha AI Enforcement | {timestamp}"
    cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 36), (0, 0, 0), -1)
    cv2.putText(canvas, overlay, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    return canvas


def build_vehicle_enforcement_records(
    vehicles: list[VehicleRecord],
    violations: list[ViolationRecord],
    plates_by_vehicle: dict[str, PlateResult],
) -> list[VehicleEnforcementRecord]:
    by_vehicle: dict[str, list[ViolationRecord]] = {}
    for v in violations:
        by_vehicle.setdefault(v.vehicle_id, []).append(v)

    records: list[VehicleEnforcementRecord] = []
    for vehicle in vehicles:
        v_violations = by_vehicle.get(vehicle.vehicle_id, [])
        plate = plates_by_vehicle.get(vehicle.vehicle_id) or plates_by_vehicle.get(vehicle.track_id)
        records.append(
            VehicleEnforcementRecord(
                vehicle_id=vehicle.vehicle_id,
                vehicle_type=vehicle.vehicle_type,
                track_id=vehicle.track_id,
                bounding_box=vehicle.bbox,
                license_plate=plate,
                associated_persons=[
                    AssociatedPersonOut(
                        person_id=p.person_id,
                        role=p.role,
                        bbox=p.bbox,
                        confidence=p.confidence,
                        helmet_id=p.helmet_id,
                        helmet_detected=p.helmet_detected,
                        proximity_score=p.proximity_score,
                    )
                    for p in vehicle.associated_persons
                ],
                rider_count=vehicle.rider_count,
                violations=[
                    {
                        "type": v.violation_type,
                        "confidence": v.confidence,
                        "reason": v.reason,
                        "evidence_bboxes": v.evidence_bboxes,
                    }
                    for v in v_violations
                ],
                compliance_status="violation" if v_violations else "compliant",
                confidence=vehicle.confidence,
            )
        )
    return records


def build_enforcement_result(
    media_id: str,
    job_id: str,
    image: np.ndarray,
    vehicles: list[VehicleRecord],
    violations: list[ViolationRecord],
    detections: list[Detection],
    derived: list[Detection],
    preprocessing: PreprocessingMetadata,
    plates_by_vehicle: dict[str, PlateResult],
    captured_at: str,
    congestion: CongestionResult | None = None,
    temporal_evidence: dict | None = None,
    annotated_video_path: str = "",
) -> tuple[EnforcementResult, str]:
    by_vehicle: dict[str, list[ViolationRecord]] = {}
    for v in violations:
        by_vehicle.setdefault(v.vehicle_id, []).append(v)

    timestamp = captured_at or datetime.now(timezone.utc).isoformat()
    annotated = render_enforcement_image(image, vehicles, by_vehicle, timestamp)
    annotated_path = EVIDENCE_DIR / f"{media_id}_enforcement.jpg"
    cv2.imwrite(str(annotated_path), annotated)

    vehicle_records = build_vehicle_enforcement_records(vehicles, violations, plates_by_vehicle)
    result = EnforcementResult(
        media_id=media_id,
        job_id=job_id,
        timestamp=timestamp,
        vehicles=vehicle_records,
        all_detections=detections,
        derived_objects=derived,
        annotated_path=str(annotated_path),
        annotated_video_path=annotated_video_path or "",
        preprocessing=preprocessing.model_dump(),
        congestion=congestion,
        temporal_evidence=temporal_evidence or {},
    )

    json_path = EVIDENCE_DIR / f"{media_id}_enforcement.json"
    json_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result, str(annotated_path)


def load_enforcement_for_media(media_id: str) -> EnforcementResult | None:
    """Load persisted enforcement JSON for a completed job."""
    json_path = EVIDENCE_DIR / f"{media_id}_enforcement.json"
    if not json_path.exists():
        return None
    try:
        return EnforcementResult.model_validate_json(json_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _vehicle_area(vehicle: VehicleRecord) -> float:
    x1, y1, x2, y2 = vehicle.bbox
    return max(x2 - x1, 1.0) * max(y2 - y1, 1.0)


def _expand_bbox(bbox: list[float], shape: tuple[int, ...], pad_ratio: float = 0.25) -> list[int]:
    h, w = shape[:2]
    x1, y1, x2, y2 = bbox
    bw, bh = max(x2 - x1, 1.0), max(y2 - y1, 1.0)
    pad_x, pad_y = bw * pad_ratio, bh * pad_ratio
    return [
        max(0, int(x1 - pad_x)),
        max(0, int(y1 - pad_y)),
        min(w, int(x2 + pad_x)),
        min(h, int(y2 + pad_y)),
    ]


def render_focused_evidence_image(
    image: np.ndarray,
    vehicle: VehicleRecord,
    violations: list[ViolationRecord],
    timestamp: str,
) -> np.ndarray:
    """Crop and annotate the primary violating vehicle — main subject in evidence."""
    ex1, ey1, ex2, ey2 = _expand_bbox(vehicle.bbox, image.shape, pad_ratio=0.30)
    crop = image[ey1:ey2, ex1:ex2].copy()

    def _shift(bbox: list[float]) -> list[float]:
        return [bbox[0] - ex1, bbox[1] - ey1, bbox[2] - ex1, bbox[3] - ey1]

    types = ", ".join(v.violation_type for v in violations)
    _draw_bbox(crop, _shift(vehicle.bbox), f"{vehicle.vehicle_id} | {types}", VIOLATION_COLOR)

    person_bboxes: set[tuple] = set()
    for v in violations:
        for b in v.evidence_bboxes:
            if b == vehicle.bbox:
                continue
            key = tuple(round(x, 1) for x in b)
            if key in person_bboxes:
                continue
            person_bboxes.add(key)
            _draw_bbox(crop, _shift(b), v.violation_type[:12], VIOLATION_COLOR)

    overlay = f"Nigha AI | {vehicle.vehicle_id} | {timestamp[:19]}"
    cv2.rectangle(crop, (0, 0), (crop.shape[1], 32), (0, 0, 0), -1)
    cv2.putText(crop, overlay, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
    return crop


def _merge_violations(violations: list[ViolationRecord]) -> dict[str, Any]:
    types = sorted({v.violation_type for v in violations})
    bboxes: list[list[float]] = []
    seen: set[tuple] = set()
    for v in violations:
        for b in v.evidence_bboxes:
            key = tuple(round(x, 1) for x in b)
            if key not in seen:
                seen.add(key)
                bboxes.append(b)
    return {
        "type": ",".join(types),
        "types": types,
        "confidence": max(v.confidence for v in violations),
        "reason": " | ".join(f"{v.violation_type}: {v.reason}" for v in violations),
        "evidence_bboxes": bboxes,
        "violations": [
            {
                "type": v.violation_type,
                "confidence": v.confidence,
                "reason": v.reason,
                "evidence_bboxes": v.evidence_bboxes,
            }
            for v in violations
        ],
    }


def build_evidence_packages(
    media_id: str,
    image: np.ndarray,
    vehicles: list[VehicleRecord],
    violations: list[ViolationRecord],
    preprocessing: PreprocessingMetadata,
    latitude: Optional[float],
    longitude: Optional[float],
    camera_id: Optional[str],
    captured_at: str,
    plates_by_vehicle: dict[str, PlateResult],
    annotated_path: str,
) -> list[EvidencePackage]:
    """One evidence package per vehicle — all violation types merged on the same record."""
    timestamp = captured_at or datetime.now(timezone.utc).isoformat()
    packages: list[EvidencePackage] = []
    vehicle_map = {v.vehicle_id: v for v in vehicles}

    by_vehicle: dict[str, list[ViolationRecord]] = {}
    for violation in violations:
        by_vehicle.setdefault(violation.vehicle_id, []).append(violation)

    for vehicle_id, v_violations in by_vehicle.items():
        vehicle = vehicle_map.get(vehicle_id)
        if not vehicle:
            continue
        plate = plates_by_vehicle.get(vehicle_id) or plates_by_vehicle.get(v_violations[0].track_id)
        evidence_id = str(uuid.uuid4())
        merged = _merge_violations(v_violations)
        focused = render_focused_evidence_image(image, vehicle, v_violations, timestamp)
        focus_path = EVIDENCE_DIR / f"{evidence_id}_focus.jpg"
        cv2.imwrite(str(focus_path), focused)

        package = EvidencePackage(
            evidence_id=evidence_id,
            media_id=media_id,
            timestamp=timestamp,
            location={"lat": latitude, "lng": longitude, "camera_id": camera_id},
            vehicle={
                "vehicle_id": vehicle_id,
                "track_id": vehicle.track_id,
                "class": vehicle.vehicle_type,
                "plate": plate.plate_normalized if plate else "",
            },
            violation=merged,
            preprocessing=preprocessing.model_dump(),
            review_status="pending_review",
            annotated_path=str(focus_path),
        )
        packages.append(package)
        json_path = EVIDENCE_DIR / f"{evidence_id}.json"
        json_path.write_text(package.model_dump_json(indent=2), encoding="utf-8")

    if not violations and vehicles:
        primary = max(vehicles, key=_vehicle_area)
        plate = plates_by_vehicle.get(primary.vehicle_id) or plates_by_vehicle.get(primary.track_id)
        evidence_id = str(uuid.uuid4())
        package = EvidencePackage(
            evidence_id=evidence_id,
            media_id=media_id,
            timestamp=timestamp,
            location={"lat": latitude, "lng": longitude, "camera_id": camera_id},
            vehicle={
                "vehicle_id": primary.vehicle_id,
                "track_id": primary.track_id,
                "class": primary.vehicle_type,
                "plate": plate.plate_normalized if plate else "",
            },
            violation={
                "type": "none",
                "types": [],
                "confidence": 0.0,
                "reason": "No violations detected",
                "evidence_bboxes": [],
                "violations": [],
            },
            preprocessing=preprocessing.model_dump(),
            review_status="auto_cleared",
            annotated_path=annotated_path,
        )
        packages.append(package)

    return packages
