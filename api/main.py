"""Nigha AI FastAPI application."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from config import EVIDENCE_DIR, UPLOAD_DIR, ensure_dirs, settings
from db.database import get_db, init_db
from db.models import AuditLog, Evidence, Media, ProcessingJob
from schemas import (
    AnalyticsSummary,
    ChallanExportResponse,
    EvidenceSearchParams,
    FeedbackStats,
    JobStatusResponse,
    MediaUploadResponse,
    MetricsResponse,
    MobilityAnalytics,
    QueueStatusResponse,
    RTSPCaptureRequest,
    SceneConfig,
)
from services.analytics.mobility import get_mobility_analytics
from services.analytics.service import get_analytics_summary, get_metrics, search_evidence
from services.challan.export import build_challan_export, mask_plate, save_challan_receipt
from services.feedback.service import get_feedback_stats, record_rejection_feedback
from services.ingestion.service import save_upload
from services.jobs.events import job_events
from services.jobs.queue import enqueue_job, queue_status
from services.pipeline import process_media_job
from services.security.auth import create_access_token, get_current_user, require_role
from services.security.paths import resolve_under

ensure_dirs()
init_db()

app = FastAPI(title=settings.app_name, version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
except ImportError:
    limiter = None


@app.on_event("startup")
def _warmup_models() -> None:
    if not settings.warmup_enabled:
        return
    from services.warmup import start_warmup_background, warmup_all

    if settings.warmup_blocking:
        warmup_all()
    else:
        start_warmup_background()


def _get_media(db: Session, media_id: str) -> Media:
    media = db.query(Media).filter(Media.media_id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    return media


def _run_job(media_id: str, job_id: str, scene: SceneConfig) -> None:
    from db.database import SessionLocal

    db = SessionLocal()
    try:
        media = db.query(Media).filter(Media.media_id == media_id).first()
        if not media:
            job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = f"Media not found: {media_id}"
                job.completed_at = datetime.now(timezone.utc).isoformat()
                db.commit()
            return
        process_media_job(db, media, scene_config=scene, job_id=job_id)
    except Exception as exc:
        job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = str(exc)
            job.completed_at = datetime.now(timezone.utc).isoformat()
            db.commit()
    finally:
        db.close()


def _sanitize_query(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned or cleaned.lower() == "undefined":
        return None
    return cleaned


def _parse_scene(
    legal_direction_angle: float = 0.0,
    no_parking_zones: Optional[str] = None,
    stop_line_y: Optional[float] = None,
    traffic_light_state: str = "unknown",
    signal_state: str = "unknown",
) -> SceneConfig:
    zones = []
    if no_parking_zones:
        try:
            zones = json.loads(no_parking_zones)
        except json.JSONDecodeError:
            zones = []
    return SceneConfig(
        legal_direction_angle=legal_direction_angle or 0.0,
        no_parking_zones=zones,
        stop_line_y=stop_line_y,
        traffic_light_state=traffic_light_state or "unknown",
        signal_state=signal_state or "unknown",
    )


@app.get("/health")
def health() -> dict:
    from services.warmup import get_status

    qs = queue_status()
    warm = get_status()
    return {
        "status": "ok" if warm["ready"] or not settings.warmup_enabled else "starting",
        "app": settings.app_name,
        "version": "2.0.0",
        "port": settings.api_port,
        "models_ready": warm["ready"] or not settings.warmup_enabled,
        "models_warming": warm["warming"],
        "models_loaded": warm["models"],
        "warmup_error": warm["error"],
        "features": [
            "per_vehicle_enforcement",
            "congestion_classification",
            "mobility_intelligence",
            "confidence_tier_routing",
            "temporal_violations",
            "audit_log",
            "challan_export",
            "active_learning_feedback",
            "websocket_jobs",
            "rtsp_ingest",
            "optional_jwt_auth",
        ],
        "queue": qs,
        "auth_enabled": settings.auth_enabled,
    }


@app.post("/api/v1/auth/token")
def issue_token(username: str = Form(...), role: str = Form("constable")) -> dict:
    if role not in {"viewer", "constable", "inspector", "admin"}:
        raise HTTPException(status_code=400, detail="Invalid role")
    token = create_access_token(username, role)
    return {"access_token": token, "token_type": "bearer", "role": role}


@app.post(f"{settings.api_prefix}/media/upload", response_model=MediaUploadResponse)
async def upload_media(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    camera_id: Optional[str] = Form(None),
    legal_direction_angle: Optional[float] = Form(0.0),
    no_parking_zones: Optional[str] = Form(None),
    stop_line_y: Optional[float] = Form(None),
    traffic_light_state: Optional[str] = Form("unknown"),
    signal_state: Optional[str] = Form("unknown"),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> MediaUploadResponse:
    try:
        media_data = await save_upload(file, latitude, longitude, camera_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    media = Media(**media_data)
    db.add(media)
    db.commit()

    scene = _parse_scene(
        legal_direction_angle or 0.0,
        no_parking_zones,
        stop_line_y,
        traffic_light_state or "unknown",
        signal_state or "unknown",
    )

    job_id = f"job-{media.media_id[:8]}"
    backend = enqueue_job(_run_job, media.media_id, job_id, scene)
    job = ProcessingJob(
        job_id=job_id,
        media_id=media.media_id,
        status="queued",
        queue_backend=backend,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(job)
    db.commit()

    if backend == "inline":
        background_tasks.add_task(_run_job, media.media_id, job_id, scene)

    return MediaUploadResponse(
        media_id=media.media_id,
        job_id=job_id,
        status="queued",
        message=f"Media uploaded — processing via {backend} queue",
    )


@app.post(f"{settings.api_prefix}/media/rtsp", response_model=MediaUploadResponse)
async def capture_rtsp(
    body: RTSPCaptureRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> MediaUploadResponse:
    """Capture a frame from RTSP and enqueue processing."""
    import cv2
    from services.ingestion.rtsp import capture_rtsp_frame

    try:
        frame = capture_rtsp_frame(body.rtsp_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    media_id = str(uuid.uuid4())
    filename = f"rtsp_{media_id[:8]}.jpg"
    path = UPLOAD_DIR / filename
    cv2.imwrite(str(path), frame)

    media = Media(
        media_id=media_id,
        filename=filename,
        media_type="image",
        stored_path=str(path),
        captured_at=datetime.now(timezone.utc).isoformat(),
        latitude=body.latitude,
        longitude=body.longitude,
        camera_id=body.camera_id,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(media)
    db.commit()

    scene = SceneConfig(legal_direction_angle=body.legal_direction_angle)
    job_id = f"job-{media_id[:8]}"
    job = ProcessingJob(
        job_id=job_id,
        media_id=media_id,
        status="queued",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(job)
    db.commit()
    background_tasks.add_task(_run_job, media_id, job_id, scene)

    return MediaUploadResponse(
        media_id=media_id,
        job_id=job_id,
        status="queued",
        message="RTSP frame captured and queued",
    )


@app.post(f"{settings.api_prefix}/media/{{media_id}}/process", response_model=JobStatusResponse)
def process_media(
    media_id: str,
    scene: Optional[SceneConfig] = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> JobStatusResponse:
    media = _get_media(db, media_id)
    return process_media_job(db, media, scene_config=scene or SceneConfig())


@app.get(f"{settings.api_prefix}/jobs/{{job_id}}", response_model=JobStatusResponse)
def get_job(job_id: str, db: Session = Depends(get_db)) -> JobStatusResponse:
    job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    evidence_rows = db.query(Evidence).filter(Evidence.job_id == job_id).all()
    from services.analytics.service import _evidence_to_dict
    from services.evidence.service import load_enforcement_for_media

    evidence = []
    congestion = None
    for row in evidence_rows:
        item = _evidence_to_dict(row)
        evidence.append(
            {
                "evidence_id": item["evidence_id"],
                "media_id": item["media_id"],
                "timestamp": item["created_at"],
                "location": {
                    "lat": item["latitude"],
                    "lng": item["longitude"],
                    "camera_id": item["camera_id"],
                },
                "vehicle": {
                    "vehicle_id": item.get("vehicle_id"),
                    "track_id": item["track_id"],
                    "class": item["vehicle_class"],
                    "plate": mask_plate(item["plate_normalized"]),
                },
                "violation": {
                    "type": item["violation_type"],
                    "confidence": item["confidence"],
                    "reason": item["reason"],
                    "evidence_bboxes": item["evidence_bboxes"],
                },
                "preprocessing": item["preprocessing"],
                "review_status": item["review_status"],
                "review_tier": item.get("review_tier"),
                "annotated_path": item.get("annotated_path") or "",
            }
        )

    enforcement = load_enforcement_for_media(job.media_id) if job.status == "completed" else None
    annotated = enforcement.annotated_path if enforcement else None
    annotated_video = enforcement.annotated_video_path if enforcement else None
    if enforcement and enforcement.congestion:
        congestion = enforcement.congestion
    if not annotated and evidence_rows:
        annotated = evidence_rows[0].annotated_path

    return JobStatusResponse(
        job_id=job.job_id,
        media_id=job.media_id,
        status=job.status,
        latency_ms=job.latency_ms,
        error_message=job.error_message,
        evidence=evidence,
        enforcement=enforcement,
        annotated_path=annotated,
        annotated_video_path=annotated_video or None,
        congestion=congestion,
        queue_backend=getattr(job, "queue_backend", None),
    )


@app.websocket(f"{settings.api_prefix}/ws/jobs/{{job_id}}")
async def job_websocket(websocket: WebSocket, job_id: str):
    await websocket.accept()
    queue = job_events.subscribe(job_id)
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
            if event.get("event") in {"completed", "failed"}:
                break
    except WebSocketDisconnect:
        pass
    finally:
        job_events.unsubscribe(job_id, queue)


@app.get(f"{settings.api_prefix}/evidence")
def list_evidence(
    plate: Optional[str] = None,
    violation_type: Optional[str] = None,
    review_status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    camera_id: Optional[str] = None,
    violations_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> list[dict]:
    params = EvidenceSearchParams(
        plate=_sanitize_query(plate),
        violation_type=_sanitize_query(violation_type),
        review_status=_sanitize_query(review_status),
        date_from=_sanitize_query(date_from),
        date_to=_sanitize_query(date_to),
        camera_id=_sanitize_query(camera_id),
        violations_only=violations_only,
        limit=limit,
        offset=offset,
    )
    items = search_evidence(db, params)
    for item in items:
        item["plate_masked"] = mask_plate(item.get("plate_normalized"))
    return items


@app.patch(f"{settings.api_prefix}/evidence/{{evidence_id}}/review")
def update_review(
    evidence_id: str,
    review_status: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("constable")),
) -> dict:
    if review_status not in {"pending_review", "confirmed", "rejected", "auto_cleared"}:
        raise HTTPException(status_code=400, detail="Invalid review status")
    row = db.query(Evidence).filter(Evidence.evidence_id == evidence_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Evidence not found")

    previous = row.review_status
    row.review_status = review_status

    officer_id = user.get("sub", "unknown")
    db.add(
        AuditLog(
            log_id=str(uuid.uuid4()),
            evidence_id=evidence_id,
            officer_id=officer_id,
            action=review_status,
            details=json.dumps({"previous": previous}),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    )

    if review_status == "rejected":
        record_rejection_feedback(db, row)

    db.commit()
    return {"evidence_id": evidence_id, "review_status": review_status, "officer_id": officer_id}


@app.post(f"{settings.api_prefix}/evidence/{{evidence_id}}/export-challan", response_model=ChallanExportResponse)
def export_challan(
    evidence_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role("constable")),
) -> ChallanExportResponse:
    row = db.query(Evidence).filter(Evidence.evidence_id == evidence_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Evidence not found")
    if row.review_status != "confirmed":
        raise HTTPException(status_code=400, detail="Evidence must be confirmed before challan export")
    challan = build_challan_export(row, officer_id=user.get("sub", "OFFICER"))
    receipt_path = save_challan_receipt(challan, evidence_id)
    return ChallanExportResponse(challan=challan, evidence_id=evidence_id, receipt_path=receipt_path)


@app.get(f"{settings.api_prefix}/analytics/summary", response_model=AnalyticsSummary)
def analytics_summary(db: Session = Depends(get_db)) -> AnalyticsSummary:
    return get_analytics_summary(db)


@app.get(f"{settings.api_prefix}/analytics/mobility", response_model=MobilityAnalytics)
def mobility_analytics(db: Session = Depends(get_db)) -> MobilityAnalytics:
    return get_mobility_analytics(db)


@app.get(f"{settings.api_prefix}/feedback/stats", response_model=FeedbackStats)
def feedback_stats(db: Session = Depends(get_db)) -> FeedbackStats:
    data = get_feedback_stats(db)
    return FeedbackStats(**data)


@app.get(f"{settings.api_prefix}/metrics", response_model=MetricsResponse)
def metrics(db: Session = Depends(get_db)) -> MetricsResponse:
    return MetricsResponse(**get_metrics(db))


@app.get(f"{settings.api_prefix}/queue/status", response_model=QueueStatusResponse)
def get_queue_status() -> QueueStatusResponse:
    return QueueStatusResponse(**queue_status())


@app.get(f"{settings.api_prefix}/files/challan/{{filename}}")
def get_challan_receipt_file(filename: str):
    if not filename.endswith("_challan.html"):
        raise HTTPException(status_code=400, detail="Invalid challan receipt file")
    path = resolve_under(EVIDENCE_DIR, filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Receipt not found")
    return FileResponse(path, media_type="text/html")


@app.get(f"{settings.api_prefix}/files/annotated/{{filename}}")
def get_annotated_file(filename: str):
    path = resolve_under(EVIDENCE_DIR, filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)


@app.get(f"{settings.api_prefix}/files/upload/{{filename}}")
def get_upload_file(filename: str):
    path = resolve_under(UPLOAD_DIR, filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)


frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if settings.serve_frontend and frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
