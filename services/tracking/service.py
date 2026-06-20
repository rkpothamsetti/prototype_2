"""Simple IoU-based multi-frame tracking."""
from __future__ import annotations

from schemas import Detection
from services.common.utils import iou


def track_detections(frame_detections: list[list[Detection]], iou_threshold: float = 0.45) -> list[list[Detection]]:
    if not frame_detections:
        return []

    tracked_frames: list[list[Detection]] = []
    active_tracks: dict[str, Detection] = {}

    for frame_idx, detections in enumerate(frame_detections):
        assigned: set[str] = set()
        frame_out: list[Detection] = []

        for det in detections:
            best_id = None
            best_iou = 0.0
            for track_id, prev in active_tracks.items():
                if track_id in assigned:
                    continue
                if prev.class_name != det.class_name:
                    continue
                score = iou(prev.bbox, det.bbox)
                if score > best_iou:
                    best_iou = score
                    best_id = track_id

            if best_id and best_iou >= iou_threshold:
                det.track_id = best_id
                assigned.add(best_id)
            active_tracks[det.track_id] = det
            frame_out.append(det)

        tracked_frames.append(frame_out)

    return tracked_frames


def displacement_vector(detections_by_frame: list[list[Detection]], track_id: str) -> tuple[float, float]:
    centers: list[tuple[float, float]] = []
    for frame in detections_by_frame:
        for det in frame:
            if det.track_id == track_id:
                x1, y1, x2, y2 = det.bbox
                centers.append(((x1 + x2) / 2.0, (y1 + y2) / 2.0))
                break

    if len(centers) < 2:
        return 0.0, 0.0

    dx = centers[-1][0] - centers[0][0]
    dy = centers[-1][1] - centers[0][1]
    return dx, dy
