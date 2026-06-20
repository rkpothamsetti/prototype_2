"""Heuristic congestion classification from vehicle detections."""
from __future__ import annotations

from schemas import CongestionResult, Detection


def classify_congestion(
    detections: list[Detection],
    image_shape: tuple[int, int, int] | None = None,
) -> CongestionResult:
    """
    Classify traffic congestion from detection density.
    Levels: free_flow, moderate, heavy, gridlock.
    """
    vehicles = [d for d in detections if d.class_name in {"car", "motorcycle", "bus", "truck", "bicycle"}]
    count = len(vehicles)

    density_score = 0.0
    if image_shape and len(image_shape) >= 2:
        h, w = image_shape[:2]
        frame_area = max(h * w, 1)
        occupied = sum(max(0.0, (d.bbox[2] - d.bbox[0]) * (d.bbox[3] - d.bbox[1])) for d in vehicles)
        density_score = min(1.0, occupied / (frame_area * 0.35))

    combined = min(1.0, (count / 25.0) * 0.55 + density_score * 0.45)

    if combined < 0.25:
        level = "free_flow"
        confidence = 0.85
    elif combined < 0.50:
        level = "moderate"
        confidence = 0.80
    elif combined < 0.75:
        level = "heavy"
        confidence = 0.82
    else:
        level = "gridlock"
        confidence = 0.88

    return CongestionResult(
        congestion_level=level,
        vehicle_count=count,
        density_score=round(density_score, 4),
        combined_score=round(combined, 4),
        confidence=confidence,
    )
