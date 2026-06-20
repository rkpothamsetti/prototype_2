"""
Seated-rider detection without relying on rectangular bbox overlap alone.

Uses a motorcycle *seat trapezium* (better fit for Indian bikes than axis-aligned boxes)
and optional MediaPipe pose landmarks to distinguish seated riders from standing
officers/pedestrians beside the vehicle.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

import cv2
import numpy as np

from services.common.utils import center_of_bbox, crop_image, overlap_fraction


def motorcycle_seat_trapezium(vehicle_bbox: list[float]) -> np.ndarray:
    """
    Seat occupancy region for a motorcycle — trapezium wider at the seat, narrow above.
    Extends above the bike bbox to cover rider/pillion stack (amodal-style), unlike a
    plain vehicle rectangle that misses bodies above the fuel tank.
    """
    x1, y1, x2, y2 = vehicle_bbox
    w, h = max(x2 - x1, 1.0), max(y2 - y1, 1.0)
    top_y = y1 - h * 0.42
    return np.array(
        [
            [x1 + w * 0.12, top_y],
            [x2 - w * 0.12, top_y],
            [x2 - w * 0.03, y2 - h * 0.10],
            [x1 + w * 0.03, y2 - h * 0.10],
        ],
        dtype=np.float32,
    )


def _hip_anchor(person_bbox: list[float]) -> tuple[float, float]:
    x1, y1, x2, y2 = person_bbox
    return (x1 + x2) / 2, y1 + (y2 - y1) * 0.62


def _point_in_trapezium(px: float, py: float, trapezium: np.ndarray) -> bool:
    return cv2.pointPolygonTest(trapezium, (float(px), float(py)), False) >= 0


def is_likely_child(
    person_bbox: list[float],
    vehicle_bbox: list[float] | None = None,
) -> bool:
    """Compact stature — excluded from triple-riding rider counts."""
    px1, py1, px2, py2 = person_bbox
    ph = max(py2 - py1, 1.0)
    pw = max(px2 - px1, 1.0)

    if vehicle_bbox is not None:
        vh = max(vehicle_bbox[3] - vehicle_bbox[1], 1.0)
        vw = max(vehicle_bbox[2] - vehicle_bbox[0], 1.0)
        if ph < vh * 0.38:
            return True
        if ph < vh * 0.42 and pw < vw * 0.22:
            return True
        if ph < 100 and ph / pw < 1.25 and pw < vw * 0.25:
            return True

    if ph < 70 and ph / pw < 1.2:
        return True
    return False


def _is_standing_beside_bike(person_bbox: list[float], vehicle_bbox: list[float]) -> bool:
    """Heuristics for upright pedestrians / traffic police next to a motorcycle."""
    px1, py1, px2, py2 = person_bbox
    vx1, vy1, vx2, vy2 = vehicle_bbox
    ph = max(py2 - py1, 1.0)
    pw = max(px2 - px1, 1.0)
    vh = max(vy2 - vy1, 1.0)
    hip_x, hip_y = _hip_anchor(person_bbox)
    vcx = (vx1 + vx2) / 2

    # Feet clearly on the ground below the bike (standing beside / in front)
    if py2 > vy2 + vh * 0.08:
        return True

    # Hip far to the side — beside the bike, not on the seat
    vw = max(vx2 - vx1, 1.0)
    if abs(hip_x - vcx) > vw * 0.48:
        return True

    # Tall, narrow silhouette typical of standing adults
    if ph / pw > 2.6 and hip_y > vy1 + vh * 0.35:
        return True

    return False


@lru_cache(maxsize=1)
def _load_pose():
    import mediapipe as mp

    return mp.solutions.pose.Pose(static_image_mode=True, model_complexity=0, min_detection_confidence=0.4)


def _pose_suggests_seated(image: np.ndarray, person_bbox: list[float]) -> Optional[bool]:
    """
    Optional pose check: bent knees / compressed leg span → seated.
    Returns None when MediaPipe is unavailable or no landmarks detected.
    """
    try:
        pose = _load_pose()
    except Exception:
        return None

    crop = crop_image(image, person_bbox)
    if crop.size <= 3:
        return None

    rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    try:
        result = pose.process(rgb)
    except Exception:
        return None

    if not result.pose_landmarks:
        return None

    lm = result.pose_landmarks.landmark
    h, w = crop.shape[:2]

    def y_norm(idx: int) -> float:
        return lm[idx].y * h

    hip_y = (y_norm(23) + y_norm(24)) / 2
    knee_y = (y_norm(25) + y_norm(26)) / 2
    ankle_y = (y_norm(27) + y_norm(28)) / 2
    leg_span = ankle_y - hip_y
    thigh = knee_y - hip_y

    # Seated on bike: knees bent, ankles not far below hips
    if leg_span < h * 0.42 and thigh > h * 0.04:
        return True
    if leg_span > h * 0.58:
        return False
    return None


def is_seated_on_motorcycle(
    image: np.ndarray,
    person_bbox: list[float],
    vehicle_bbox: list[float],
    min_trapezium_overlap: float = 0.18,
) -> bool:
    """
    True when a person is seated on the motorcycle (not standing beside it).
    Combines seat trapezium occupancy, anti-standing heuristics, and optional pose.
    """
    if _is_standing_beside_bike(person_bbox, vehicle_bbox):
        return False

    if is_likely_child(person_bbox, vehicle_bbox):
        return False

    trap = motorcycle_seat_trapezium(vehicle_bbox)
    px1, py1, px2, py2 = person_bbox
    ph = max(py2 - py1, 1.0)
    vx1, vy1, vx2, vy2 = vehicle_bbox
    vh = max(vy2 - vy1, 1.0)

    hip_x, hip_y = _hip_anchor(person_bbox)
    if not _point_in_trapezium(hip_x, hip_y, trap):
        return False

    # Lower torso should still overlap bike bbox (guards partial false positives)
    px1, py1, px2, py2 = person_bbox
    ph = max(py2 - py1, 1.0)
    lower_person = [px1, py1 + ph * 0.45, px2, py2]
    if overlap_fraction(lower_person, vehicle_bbox) < min_trapezium_overlap:
        return False

    pcx, pcy = center_of_bbox(person_bbox)
    vx1, vy1, vx2, vy2 = vehicle_bbox
    vh = max(vy2 - vy1, 1.0)
    if pcy > vy2 + vh * 0.12:
        return False

    pose_hint = _pose_suggests_seated(image, person_bbox)
    if pose_hint is False:
        return False

    return True


def seated_overlap_score(person_bbox: list[float], vehicle_bbox: list[float]) -> float:
    """Overlap fraction inside the seat trapezium (for triple-riding threshold)."""
    trap = motorcycle_seat_trapezium(vehicle_bbox)
    x1, y1, x2, y2 = person_bbox
    samples = 0
    inside = 0
    for fx in (0.25, 0.5, 0.75):
        for fy in (0.5, 0.65, 0.8):
            px = x1 + (x2 - x1) * fx
            py = y1 + (y2 - y1) * fy
            samples += 1
            if _point_in_trapezium(px, py, trap):
                inside += 1
    return inside / max(samples, 1)
