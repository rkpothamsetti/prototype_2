"""Mobility intelligence — congestion × violations × deployment priority."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from db.models import CongestionSnapshot, Evidence, ProcessingJob
from schemas import MobilityAnalytics

CONGESTION_WEIGHT = {"free_flow": 0.1, "moderate": 0.4, "heavy": 0.7, "gridlock": 1.0}

ZONE_NAMES = {
    "CAM_BLR_MG_01": "MG Road",
    "CAM_BLR_SILK_01": "Silk Board",
    "CAM_BLR_HEBBAL_01": "Hebbal Flyover",
    "CAM_BLR_ECITY_01": "Electronic City",
    "CAM_BLR_INDIRA_01": "Indiranagar",
}


def _congestion_weight(level: str) -> float:
    return CONGESTION_WEIGHT.get(level, 0.3)


def get_mobility_analytics(db: Session) -> MobilityAnalytics:
    evidence_rows = db.query(Evidence).filter(Evidence.violation_type != "none").all()
    congestion_rows = db.query(CongestionSnapshot).all()

    zone_violations: dict[str, int] = Counter()
    zone_types: dict[str, Counter] = defaultdict(Counter)
    hour_violations: dict[int, int] = Counter()
    hour_congestion: dict[int, list[float]] = defaultdict(list)

    for row in evidence_rows:
        cam = row.camera_id or "unknown"
        zone_violations[cam] += 1
        zone_types[cam][row.violation_type] += 1
        try:
            hour = datetime.fromisoformat(row.created_at.replace("Z", "+00:00")).hour
            hour_violations[hour] += 1
        except Exception:
            pass

    zone_congestion: dict[str, list[str]] = defaultdict(list)
    for snap in congestion_rows:
        cam = snap.camera_id or "unknown"
        zone_congestion[cam].append(snap.congestion_level)
        try:
            hour = datetime.fromisoformat(snap.created_at.replace("Z", "+00:00")).hour
            hour_congestion[hour].append(_congestion_weight(snap.congestion_level))
        except Exception:
            pass

    zones: list[dict[str, Any]] = []
    all_cameras = set(zone_violations.keys()) | set(zone_congestion.keys())
    for camera_id in all_cameras:
        violations = zone_violations.get(camera_id, 0)
        levels = zone_congestion.get(camera_id, ["moderate"])
        avg_level = max(set(levels), key=levels.count) if levels else "moderate"
        top_type = zone_types[camera_id].most_common(1)[0][0] if zone_types[camera_id] else "none"
        priority = min(
            1.0,
            (violations / 20.0) * 0.5 + _congestion_weight(avg_level) * 0.5,
        )
        zones.append(
            {
                "camera_id": camera_id,
                "zone_name": ZONE_NAMES.get(camera_id, camera_id),
                "congestion_avg": avg_level,
                "violations_total": violations,
                "top_violation": top_type,
                "priority_score": round(priority, 3),
                "deploy_recommendation": _deploy_hint(avg_level, violations, top_type),
            }
        )

    zones.sort(key=lambda z: z["priority_score"], reverse=True)

    peak_hours = []
    for hour in range(24):
        v = hour_violations.get(hour, 0)
        c_vals = hour_congestion.get(hour, [])
        c_avg = sum(c_vals) / len(c_vals) if c_vals else 0.0
        peak_hours.append({"hour": hour, "violations": v, "congestion_index": round(c_avg, 3)})

    correlation = _congestion_violation_correlation(evidence_rows, congestion_rows)

    auto_cleared = sum(1 for r in evidence_rows if r.review_status == "auto_cleared")
    pending = sum(1 for r in evidence_rows if r.review_status == "pending_review")
    total = len(evidence_rows) or 1
    officer_load_reduction = round(auto_cleared / total, 3)

    jobs = db.query(ProcessingJob).filter(ProcessingJob.status == "completed").all()
    avg_latency = 0.0
    if jobs:
        avg_latency = sum(j.latency_ms or 0 for j in jobs) / len(jobs)

    return MobilityAnalytics(
        zones=zones,
        peak_hours=peak_hours,
        congestion_violation_correlation=correlation,
        officer_load_reduction_pct=officer_load_reduction,
        pending_review_count=pending,
        avg_processing_ms=round(avg_latency, 2),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def _deploy_hint(congestion: str, violations: int, top_type: str) -> str:
    if congestion in {"heavy", "gridlock"} and violations >= 5:
        return f"Deploy officers — {top_type.replace('_', ' ')} hotspot during peak congestion"
    if violations >= 10:
        return f"Increase patrol — high {top_type.replace('_', ' ')} frequency"
    if congestion == "gridlock":
        return "Monitor congestion; consider traffic diversion"
    return "Routine monitoring"


def _congestion_violation_correlation(
    evidence_rows: list[Evidence],
    congestion_rows: list[CongestionSnapshot],
) -> float:
    if not evidence_rows or not congestion_rows:
        return 0.0
    by_cam_e: dict[str, int] = Counter(r.camera_id or "unknown" for r in evidence_rows)
    by_cam_c: dict[str, float] = {}
    for snap in congestion_rows:
        cam = snap.camera_id or "unknown"
        by_cam_c[cam] = by_cam_c.get(cam, 0.0) + _congestion_weight(snap.congestion_level)

    shared = set(by_cam_e.keys()) & set(by_cam_c.keys())
    if len(shared) < 2:
        return 0.5
    xs = [by_cam_e[c] for c in shared]
    ys = [by_cam_c[c] for c in shared]
    return round(_pearson(xs, ys), 3)


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = sum((x - mx) ** 2 for x in xs) ** 0.5
    den_y = sum((y - my) ** 2 for y in ys) ** 0.5
    if den_x == 0 or den_y == 0:
        return 0.0
    return max(-1.0, min(1.0, num / (den_x * den_y)))


def save_congestion_snapshot(
    db: Session,
    job_id: str,
    media_id: str,
    camera_id: str | None,
    congestion: dict[str, Any],
) -> None:
    snap = CongestionSnapshot(
        snapshot_id=f"snap-{job_id[:12]}",
        job_id=job_id,
        media_id=media_id,
        camera_id=camera_id,
        congestion_level=congestion.get("congestion_level", "moderate"),
        vehicle_count=congestion.get("vehicle_count", 0),
        density_score=congestion.get("density_score", 0.0),
        snapshot_json=json.dumps(congestion),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(snap)
