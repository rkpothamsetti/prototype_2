"""Per-vehicle violation evaluation — every violation linked to vehicle_id."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import yaml

from schemas import PreprocessingMetadata, SceneConfig, ViolationRecord
from services.association.engine import VehicleRecord
from services.association.pose_rider import is_likely_child, is_seated_on_motorcycle, seated_overlap_score
from services.common.utils import (
    angle_difference,
    bbox_orientation_deg,
    center_of_bbox,
    crop_image,
    overlap_fraction,
    point_in_rect,
    quality_factor_from_score,
)
from services.violation_reasoning.helmet_eval import (
    assess_rider_helmet,
    get_helmet_yolo_detections,
)

RULES_PATH = Path(__file__).resolve().parents[2] / "CONTEXT" / "violation_rules.yaml"


def _load_rules() -> dict:
    with open(RULES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def evaluate_vehicle_violations(
    image: np.ndarray,
    vehicle: VehicleRecord,
    metadata: PreprocessingMetadata,
    scene: SceneConfig,
    frame_tracks: Optional[list] = None,
    helmet_image: Optional[np.ndarray] = None,
) -> list[ViolationRecord]:
    """Evaluate all violation types for a single vehicle. Never returns global violations."""
    rules = _load_rules()
    conf = rules.get("confidence", {})
    q_factor = quality_factor_from_score(
        metadata.quality_score,
        conf.get("quality_factor_min", 0.7),
        conf.get("quality_factor_max", 1.0),
    )
    violations: list[ViolationRecord] = []
    vid = vehicle.vehicle_id
    tid = vehicle.track_id
    vtype = vehicle.vehicle_type
    bbox = vehicle.bbox

    helmet_img = helmet_image if helmet_image is not None else image

    # Helmet non-compliance (motorcycle seated adult riders only)
    helmet_cfg = rules["violations"]["helmet_non_compliance"]
    if vtype == "motorcycle":
        riders = [p for p in vehicle.associated_persons if p.role == "rider"]
        helmet_dets = get_helmet_yolo_detections(helmet_img)
        unhelmeted: list[tuple] = []
        for rider in riders:
            if is_likely_child(rider.bbox, bbox):
                continue
            assessment = assess_rider_helmet(
                helmet_img, rider.bbox, helmet_img.shape, helmet_dets=helmet_dets
            )
            score = assessment.presence_score
            if score < helmet_cfg["helmet_confidence_threshold"]:
                unhelmeted.append((rider, assessment, score))
        if unhelmeted:
            rois: list[list[float]] = []
            reasons: list[str] = []
            for rider, assessment, score in unhelmeted:
                rois.extend(assessment.head_rois)
                reasons.append(
                    helmet_cfg["reason_template"].format(score=score) + f" [{assessment.method}]"
                )
            violations.append(
                ViolationRecord(
                    violation_type="helmet_non_compliance",
                    confidence=round(
                        min(vehicle.confidence, 1.0 - min(s for _, _, s in unhelmeted)) * q_factor,
                        4,
                    ),
                    reason="; ".join(reasons),
                    evidence_bboxes=rois + [bbox],
                    vehicle_class=vtype,
                    track_id=tid,
                    vehicle_id=vid,
                )
            )

    # Triple riding — seated adult riders only (no standing bystanders or children)
    triple_cfg = rules["violations"]["triple_riding"]
    seated_riders = [
        p
        for p in vehicle.associated_persons
        if p.role == "rider"
        and not is_likely_child(p.bbox, bbox)
        and is_seated_on_motorcycle(image, p.bbox, bbox)
        and seated_overlap_score(p.bbox, bbox) >= triple_cfg.get("person_motorcycle_iou", 0.3) * 0.35
    ]
    if vtype == "motorcycle" and len(seated_riders) >= triple_cfg["min_persons"]:
        violations.append(
            ViolationRecord(
                violation_type="triple_riding",
                confidence=round(vehicle.confidence * q_factor, 4),
                reason=triple_cfg["reason_template"].format(count=len(seated_riders)),
                evidence_bboxes=[bbox] + [p.bbox for p in seated_riders],
                vehicle_class=vtype,
                track_id=tid,
                vehicle_id=vid,
            )
        )

    # Illegal parking
    parking_cfg = rules["violations"]["illegal_parking"]
    if vtype in parking_cfg["applies_to"]:
        cx, cy = center_of_bbox(bbox)
        for zone in scene.no_parking_zones:
            if point_in_rect(cx, cy, zone):
                violations.append(
                    ViolationRecord(
                        violation_type="illegal_parking",
                        confidence=round(vehicle.confidence * q_factor, 4),
                        reason=parking_cfg["reason_template"],
                        evidence_bboxes=[bbox, zone],
                        vehicle_class=vtype,
                        track_id=tid,
                        vehicle_id=vid,
                    )
                )

    # Wrong-side driving — temporal motion preferred for video
    wrong_cfg = rules["violations"]["wrong_side_driving"]
    if vtype in wrong_cfg["applies_to"]:
        temporal_triggered = False
        if frame_tracks and tid:
            from services.tracking.service import displacement_vector

            dx, dy = displacement_vector(frame_tracks, tid)
            if abs(dx) + abs(dy) > 15:
                motion_angle = math.degrees(math.atan2(dy, dx))
                diff = angle_difference(motion_angle, scene.legal_direction_angle)
                if diff > wrong_cfg["opposing_angle_deg"]:
                    temporal_triggered = True
                    violations.append(
                        ViolationRecord(
                            violation_type="wrong_side_driving",
                            confidence=round(min(0.95, vehicle.confidence * q_factor * 0.95), 4),
                            reason=(
                                f"Temporal motion angle {motion_angle:.1f}° opposes legal flow "
                                f"{scene.legal_direction_angle:.1f}° (Δ={diff:.1f}°, dx={dx:.0f}, dy={dy:.0f})"
                            ),
                            evidence_bboxes=[bbox],
                            vehicle_class=vtype,
                            track_id=tid,
                            vehicle_id=vid,
                        )
                    )
        if not temporal_triggered:
            angle = bbox_orientation_deg(bbox)
            diff = angle_difference(angle, scene.legal_direction_angle)
            if diff > wrong_cfg["opposing_angle_deg"]:
                violations.append(
                    ViolationRecord(
                        violation_type="wrong_side_driving",
                        confidence=round(vehicle.confidence * q_factor * 0.9, 4),
                        reason=wrong_cfg["reason_template"].format(angle=angle, legal_angle=scene.legal_direction_angle),
                        evidence_bboxes=[bbox],
                        vehicle_class=vtype,
                        track_id=tid,
                        vehicle_id=vid,
                    )
                )

    # Seatbelt
    seatbelt_cfg = rules["violations"]["seatbelt_non_compliance"]
    if vtype in seatbelt_cfg["applies_to"]:
        for person in vehicle.associated_persons:
            if person.role != "driver":
                continue
            torso = _driver_torso_roi(person.bbox)
            belt_score = _seatbelt_visibility_score(image, torso)
            if belt_score < 0.35:
                violations.append(
                    ViolationRecord(
                        violation_type="seatbelt_non_compliance",
                        confidence=round(vehicle.confidence * q_factor * max(belt_score, 0.3), 4),
                        reason=seatbelt_cfg["reason_template"],
                        evidence_bboxes=[torso, bbox],
                        vehicle_class=vtype,
                        track_id=tid,
                        vehicle_id=vid,
                    )
                )

    # Stop-line
    if scene.stop_line_y is not None and scene.signal_state == "red" and vtype in {
        "car", "truck", "bus", "motorcycle", "bicycle"
    }:
        stop_cfg = rules["violations"]["stop_line_violation"]
        if bbox[3] > scene.stop_line_y:
            violations.append(
                ViolationRecord(
                    violation_type="stop_line_violation",
                    confidence=round(vehicle.confidence * q_factor, 4),
                    reason=stop_cfg["reason_template"],
                    evidence_bboxes=[bbox],
                    vehicle_class=vtype,
                    track_id=tid,
                    vehicle_id=vid,
                )
            )

    # Red-light
    if scene.intersection_roi and scene.traffic_light_state == "red":
        red_cfg = rules["violations"]["red_light_violation"]
        cx, cy = center_of_bbox(bbox)
        if point_in_rect(cx, cy, scene.intersection_roi):
            violations.append(
                ViolationRecord(
                    violation_type="red_light_violation",
                    confidence=round(vehicle.confidence * q_factor, 4),
                    reason=red_cfg["reason_template"],
                    evidence_bboxes=[bbox, scene.intersection_roi],
                    vehicle_class=vtype,
                    track_id=tid,
                    vehicle_id=vid,
                )
            )

    return violations


def evaluate_all_vehicles(
    image: np.ndarray,
    vehicles: list[VehicleRecord],
    metadata: PreprocessingMetadata,
    scene: SceneConfig,
    frame_tracks: Optional[list] = None,
    helmet_image: Optional[np.ndarray] = None,
) -> list[ViolationRecord]:
    all_v: list[ViolationRecord] = []
    for vehicle in vehicles:
        all_v.extend(
            evaluate_vehicle_violations(
                image, vehicle, metadata, scene, frame_tracks, helmet_image=helmet_image
            )
        )
    return all_v


def _driver_torso_roi(person_bbox: list[float]) -> list[float]:
    x1, y1, x2, y2 = person_bbox
    h = y2 - y1
    return [x1, y1 + h * 0.25, x2, y1 + h * 0.65]


def _seatbelt_visibility_score(image: np.ndarray, torso_bbox: list[float]) -> float:
    crop = crop_image(image, torso_bbox)
    if crop.size <= 3:
        return 0.0
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=30, minLineLength=20, maxLineGap=8)
    if lines is None:
        return 0.1
    diagonal = sum(
        1
        for line in lines[:10]
        if 25 < abs(math.degrees(math.atan2(line[0][3] - line[0][1], line[0][2] - line[0][0]))) < 75
    )
    return min(1.0, diagonal / 3.0)
