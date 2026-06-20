"""Instance-level detection association and vehicle ID assignment."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import cv2
import numpy as np

from schemas import Detection, SceneConfig
from services.association.pose_rider import (
    is_likely_child,
    is_seated_on_motorcycle,
    seated_overlap_score,
)
from services.common.utils import center_of_bbox, iou, overlap_fraction, point_in_rect
from services.violation_reasoning.helmet_eval import (
    assess_rider_helmet,
    get_helmet_yolo_detections,
    helmet_detected_from_score,
)

VEHICLE_CLASSES = {"motorcycle", "car", "bus", "truck", "bicycle"}
DERIVED_CLASSES = {"helmet", "seatbelt", "license_plate", "traffic_signal", "stop_line"}


@dataclass
class AssociatedPerson:
    person_id: str
    bbox: list[float]
    confidence: float
    role: str  # rider | driver | passenger | pedestrian
    helmet_id: str | None = None
    helmet_detected: bool = False
    proximity_score: float = 0.0
    seated_overlap: float = 0.0


@dataclass
class VehicleRecord:
    vehicle_id: str
    vehicle_type: str
    track_id: str
    bbox: list[float]
    confidence: float
    associated_persons: list[AssociatedPerson] = field(default_factory=list)
    rider_count: int = 0
    derived_objects: list[Detection] = field(default_factory=list)


def nms_detections(detections: list[Detection], iou_threshold: float = 0.55) -> list[Detection]:
    """Suppress overlapping boxes of the same class."""
    by_class: dict[str, list[Detection]] = {}
    for det in detections:
        by_class.setdefault(det.class_name, []).append(det)

    kept: list[Detection] = []
    for cls, dets in by_class.items():
        dets = sorted(dets, key=lambda d: d.confidence, reverse=True)
        active = list(dets)
        while active:
            best = active.pop(0)
            kept.append(best)
            active = [d for d in active if iou(best.bbox, d.bbox) < iou_threshold]
    return kept


def _proximity_score(person: Detection, vehicle: Detection) -> float:
    piou = iou(person.bbox, vehicle.bbox)
    pcx, pcy = center_of_bbox(person.bbox)
    vx1, vy1, vx2, vy2 = vehicle.bbox
    expanded = [vx1 - 30, vy1 - 120, vx2 + 30, vy2 + 30]
    inside = 1.0 if point_in_rect(pcx, pcy, expanded) else 0.0
    dist = _bbox_distance(person.bbox, vehicle.bbox)
    max_dim = max(vehicle.bbox[2] - vehicle.bbox[0], vehicle.bbox[3] - vehicle.bbox[1], 1.0)
    dist_score = max(0.0, 1.0 - dist / (max_dim * 1.2))
    return 0.5 * piou + 0.35 * inside + 0.15 * dist_score


def _bbox_distance(a: list[float], b: list[float]) -> float:
    acx, acy = center_of_bbox(a)
    bcx, bcy = center_of_bbox(b)
    return ((acx - bcx) ** 2 + (acy - bcy) ** 2) ** 0.5


def _is_motorcycle_rider(
    image: np.ndarray,
    person_bbox: list[float],
    vehicle_bbox: list[float],
) -> bool:
    """Seated rider via seat trapezium + optional pose (not rectangular bbox alone)."""
    return is_seated_on_motorcycle(image, person_bbox, vehicle_bbox)


def _motorcycle_proximity_score(
    image: np.ndarray,
    person: Detection,
    vehicle: Detection,
) -> float:
    """Stricter proximity for motorcycles — avoids counting bystanders and police."""
    if not _is_motorcycle_rider(image, person.bbox, vehicle.bbox):
        return 0.0
    piou = iou(person.bbox, vehicle.bbox)
    pcx, pcy = center_of_bbox(person.bbox)
    vx1, vy1, vx2, vy2 = vehicle.bbox
    # Tighter vertical zone than generic proximity (no 120px above bike)
    expanded = [vx1 - 20, vy1 - 40, vx2 + 20, vy2 + 15]
    inside = 1.0 if point_in_rect(pcx, pcy, expanded) else 0.0
    dist = _bbox_distance(person.bbox, vehicle.bbox)
    max_dim = max(vx2 - vx1, vy2 - vy1, 1.0)
    dist_score = max(0.0, 1.0 - dist / (max_dim * 0.9))
    return 0.55 * piou + 0.30 * inside + 0.15 * dist_score


def _derive_helmets(
    image: np.ndarray,
    persons: list[Detection],
    image_shape: tuple[int, ...] | None = None,
) -> list[Detection]:
    helmets: list[Detection] = []
    shape = image_shape or image.shape
    helmet_dets = get_helmet_yolo_detections(image)
    for person in persons:
        assessment = assess_rider_helmet(
            image, person.bbox, shape, helmet_dets=helmet_dets
        )
        if helmet_detected_from_score(assessment.presence_score):
            helmets.append(
                Detection(
                    track_id=f"HLM-{person.track_id[:8]}",
                    class_name="helmet",
                    bbox=assessment.worst_head_roi,
                    confidence=round(assessment.presence_score, 4),
                    role=f"on_person:{person.track_id}:{assessment.method}",
                )
            )
    return helmets


def _derive_traffic_signals(image: np.ndarray) -> list[Detection]:
    h, w = image.shape[:2]
    roi = image[0 : int(h * 0.35), :]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    red = cv2.inRange(hsv, np.array([0, 100, 80]), np.array([10, 255, 255]))
    green = cv2.inRange(hsv, np.array([40, 60, 60]), np.array([90, 255, 255]))
    signals: list[Detection] = []
    for mask, state in ((red, "red"), (green, "green")):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            if cv2.contourArea(cnt) < 150:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            if bw < 8 or bh < 8:
                continue
            signals.append(
                Detection(
                    track_id=f"SIG-{uuid.uuid4().hex[:8]}",
                    class_name="traffic_signal",
                    bbox=[float(x), float(y), float(x + bw), float(y + bh)],
                    confidence=0.6,
                    role=state,
                )
            )
    return signals[:6]


def _derive_stop_lines(scene: SceneConfig, image_shape: tuple[int, int, int]) -> list[Detection]:
    if scene.stop_line_y is None:
        return []
    _, w = image_shape[1], image_shape[0]
    y = scene.stop_line_y
    return [
        Detection(
            track_id=f"STL-{uuid.uuid4().hex[:6]}",
            class_name="stop_line",
            bbox=[0.0, y - 3, float(w), y + 3],
            confidence=1.0,
        )
    ]


def build_scene_graph(
    image: np.ndarray,
    detections: list[Detection],
    scene: SceneConfig,
    helmet_image: np.ndarray | None = None,
) -> tuple[list[VehicleRecord], list[Detection]]:
    """
    Build vehicle-centric scene graph with associations.
    Returns (vehicles, all_derived_detections).
    """
    detections = nms_detections(detections)
    persons = [d for d in detections if d.class_name == "person"]
    vehicles_raw = [d for d in detections if d.class_name in VEHICLE_CLASSES]

    # Infer motorcycle vehicle when only rider detected (front-facing bike photos)
    if not vehicles_raw and persons:
        p = max(persons, key=lambda x: x.confidence)
        w = p.bbox[2] - p.bbox[0]
        h = p.bbox[3] - p.bbox[1]
        vehicles_raw.append(
            Detection(
                track_id=str(uuid.uuid4()),
                class_name="motorcycle",
                bbox=[
                    p.bbox[0] - w * 0.4,
                    p.bbox[1] - h * 0.1,
                    p.bbox[2] + w * 0.4,
                    p.bbox[3] + h * 0.8,
                ],
                confidence=p.confidence * 0.85,
                role="inferred",
            )
        )

    derived: list[Detection] = []
    helmet_img = helmet_image if helmet_image is not None else image
    derived.extend(_derive_helmets(helmet_img, persons, image.shape))
    derived.extend(_derive_traffic_signals(image))
    derived.extend(_derive_stop_lines(scene, image.shape))

    vehicle_records: list[VehicleRecord] = []
    # Exclusive assignment: each person → best matching vehicle only
    person_best: dict[str, tuple[float, int]] = {}

    for v_idx, vehicle in enumerate(vehicles_raw):
        for person in persons:
            if vehicle.class_name == "motorcycle":
                score = _motorcycle_proximity_score(image, person, vehicle)
            else:
                score = _proximity_score(person, vehicle)
            if score < 0.20:
                continue
            prev = person_best.get(person.track_id)
            if prev is None or score > prev[0]:
                person_best[person.track_id] = (score, v_idx)

    for idx, vehicle in enumerate(vehicles_raw, start=1):
        vehicle_id = f"VEH-{idx:03d}"
        v_idx = idx - 1
        associated: list[AssociatedPerson] = []

        for person in persons:
            best = person_best.get(person.track_id)
            if not best or best[1] != v_idx:
                continue
            score = best[0]

            role = "pedestrian"
            seat_ov = 0.0
            if vehicle.class_name == "motorcycle" and _is_motorcycle_rider(image, person.bbox, vehicle.bbox):
                if is_likely_child(person.bbox, vehicle.bbox):
                    role = "child"
                else:
                    role = "rider"
                    seat_ov = seated_overlap_score(person.bbox, vehicle.bbox)
            elif person.role == "driver_candidate" and vehicle.class_name in {"car", "truck", "bus"}:
                role = "driver"
            elif vehicle.class_name in {"car", "truck", "bus"}:
                role = "passenger"

            helmet_id = None
            helmet_detected = False
            for hlm in derived:
                if hlm.class_name == "helmet" and hlm.role.startswith(f"on_person:{person.track_id}"):
                    helmet_id = hlm.track_id
                    helmet_detected = True
                    break

            associated.append(
                AssociatedPerson(
                    person_id=person.track_id,
                    bbox=person.bbox,
                    confidence=person.confidence,
                    role=role,
                    helmet_id=helmet_id,
                    helmet_detected=helmet_detected,
                    proximity_score=round(score, 4),
                    seated_overlap=round(seat_ov, 4),
                )
            )

        rider_count = sum(1 for a in associated if a.role == "rider")

        vehicle_records.append(
            VehicleRecord(
                vehicle_id=vehicle_id,
                vehicle_type=vehicle.class_name,
                track_id=vehicle.track_id,
                bbox=vehicle.bbox,
                confidence=vehicle.confidence,
                associated_persons=associated,
                rider_count=rider_count,
                derived_objects=[d for d in derived if d.class_name in DERIVED_CLASSES],
            )
        )

    return vehicle_records, derived
