"""Analytics and reporting service."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import CongestionSnapshot, Evidence
from schemas import AnalyticsSummary, EvidenceSearchParams


def search_evidence(db: Session, params: EvidenceSearchParams) -> list[dict]:
    query = db.query(Evidence)
    if params.plate:
        query = query.filter(Evidence.plate_normalized.ilike(f"%{params.plate.upper()}%"))
    if params.violation_type:
        vt = params.violation_type
        query = query.filter(
            (Evidence.violation_type == vt) | (Evidence.violation_type.like(f"%{vt}%"))
        )
    if params.review_status:
        query = query.filter(Evidence.review_status == params.review_status)
    if params.camera_id:
        query = query.filter(Evidence.camera_id == params.camera_id)
    if params.date_from:
        query = query.filter(Evidence.created_at >= params.date_from)
    if params.date_to:
        query = query.filter(Evidence.created_at <= params.date_to)
    if params.violations_only:
        query = query.filter(Evidence.violation_type != "none")

    rows = (
        query.order_by(Evidence.created_at.desc())
        .offset(params.offset)
        .limit(params.limit)
        .all()
    )
    return [_evidence_to_dict(row) for row in rows]


def _evidence_to_dict(row: Evidence) -> dict:
    bboxes = []
    if row.evidence_bboxes:
        try:
            bboxes = json.loads(row.evidence_bboxes)
        except json.JSONDecodeError:
            bboxes = []
    preprocessing = {}
    if row.preprocessing_json:
        try:
            preprocessing = json.loads(row.preprocessing_json)
        except json.JSONDecodeError:
            preprocessing = {}

    return {
        "evidence_id": row.evidence_id,
        "media_id": row.media_id,
        "job_id": row.job_id,
        "violation_type": row.violation_type,
        "confidence": row.confidence,
        "reason": row.reason,
        "plate_raw": row.plate_raw,
        "plate_normalized": row.plate_normalized,
        "plate_valid": bool(row.plate_valid),
        "vehicle_class": row.vehicle_class,
        "track_id": row.track_id,
        "vehicle_id": getattr(row, "vehicle_id", None),
        "latitude": row.latitude,
        "longitude": row.longitude,
        "camera_id": row.camera_id,
        "evidence_bboxes": bboxes,
        "preprocessing": preprocessing,
        "annotated_path": row.annotated_path,
        "review_status": row.review_status,
        "review_tier": getattr(row, "review_tier", None) or "standard",
        "created_at": row.created_at,
    }


def get_analytics_summary(db: Session) -> AnalyticsSummary:
    rows = db.query(Evidence).filter(Evidence.violation_type != "none").all()

    by_type: Counter = Counter()
    for row in rows:
        for vt in (row.violation_type or "").split(","):
            vt = vt.strip()
            if vt and vt != "none":
                by_type[vt] += 1
    by_review = Counter(row.review_status for row in rows)
    by_tier = Counter(getattr(row, "review_tier", None) or "standard" for row in rows)

    daily: dict[str, int] = defaultdict(int)
    for row in rows:
        day = (row.created_at or "")[:10]
        if day:
            daily[day] += 1

    daily_trends = [{"date": d, "count": daily[d]} for d in sorted(daily.keys())]

    hotspot_counter: dict[tuple[float, float, str], int] = Counter()
    for row in rows:
        if row.latitude is not None and row.longitude is not None:
            key = (round(row.latitude, 4), round(row.longitude, 4), row.camera_id or "unknown")
            hotspot_counter[key] += 1

    hotspots = [
        {
            "lat": lat,
            "lng": lng,
            "camera_id": cam,
            "count": count,
        }
        for (lat, lng, cam), count in hotspot_counter.most_common(20)
    ]

    repeat_offenders = _compute_repeat_offenders(rows)

    congestion_rows = db.query(CongestionSnapshot).all()
    congestion_summary = Counter(s.congestion_level for s in congestion_rows)
    auto_cleared = by_review.get("auto_cleared", 0)
    officer_load = round(auto_cleared / max(len(rows), 1), 3)

    return AnalyticsSummary(
        total_violations=len(rows),
        by_type=dict(by_type),
        by_review_status=dict(by_review),
        by_review_tier=dict(by_tier),
        daily_trends=daily_trends,
        hotspots=hotspots,
        repeat_offenders=repeat_offenders,
        congestion_summary=dict(congestion_summary),
        officer_load_reduction_pct=officer_load,
    )


def _compute_repeat_offenders(rows: list[Evidence]) -> list[dict]:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)
    grouped: dict[str, list[Evidence]] = defaultdict(list)

    for row in rows:
        if row.plate_normalized:
            grouped[row.plate_normalized].append(row)

    serious_types = {
        "helmet_non_compliance",
        "triple_riding",
        "wrong_side_driving",
        "red_light_violation",
        "stop_line_violation",
        "seatbelt_non_compliance",
    }

    offenders: list[dict] = []
    for plate, items in grouped.items():
        recent = 0
        serious = 0
        for item in items:
            try:
                created = datetime.fromisoformat(item.created_at.replace("Z", "+00:00"))
            except Exception:
                created = now
            if created >= cutoff:
                recent += 1
            if item.violation_type in serious_types:
                serious += 1
        risk_score = 3 * recent + 2 * serious + min(5, len(items))
        offenders.append(
            {
                "plate": plate,
                "total_violations": len(items),
                "violations_last_30d": recent,
                "serious_violations": serious,
                "risk_score": risk_score,
                "latest_violation": max(i.created_at for i in items),
            }
        )

    offenders.sort(key=lambda x: x["risk_score"], reverse=True)
    return offenders[:15]


def get_metrics(db: Session) -> dict:
    from db.models import ProcessingJob

    jobs = db.query(ProcessingJob).all()
    latencies = [j.latency_ms for j in jobs if j.latency_ms is not None and j.status == "completed"]
    latencies.sort()

    def percentile(values: list[float], p: float) -> float:
        if not values:
            return 0.0
        idx = int(len(values) * p)
        idx = min(max(idx, 0), len(values) - 1)
        return values[idx]

    completed = [j for j in jobs if j.status == "completed"]
    throughput = 0.0
    if completed:
        total_sec = sum((j.latency_ms or 0) for j in completed) / 1000.0
        throughput = len(completed) / total_sec if total_sec > 0 else 0.0

    return {
        "latency_p50_ms": percentile(latencies, 0.5),
        "latency_p95_ms": percentile(latencies, 0.95),
        "throughput_ips": round(throughput, 4),
        "total_jobs": len(jobs),
        "completed_jobs": len(completed),
        "failed_jobs": len([j for j in jobs if j.status == "failed"]),
    }
