"""End-to-end processing pipeline orchestrator."""

from __future__ import annotations



import json

import time

import uuid

from datetime import datetime, timezone

from pathlib import Path

from typing import Callable, Optional



import cv2

import numpy as np

from sqlalchemy.orm import Session



from db.models import Evidence, Media, ProcessingJob

from schemas import CongestionResult, JobStatusResponse, PlateResult, SceneConfig

from services.analytics.mobility import save_congestion_snapshot

from services.congestion.classifier import classify_congestion

from services.detection.service import detect_objects

from services.evidence.service import build_enforcement_result, build_evidence_packages

from services.jobs.events import job_events

from services.ocr.service import extract_plate_from_vehicle, find_plates_in_image

from services.preprocessing.service import preprocess_frame, preprocess_image

from services.review.tiers import classify_review_tier

from services.tracking.service import displacement_vector, track_detections

from config import settings
from services.evidence.video import write_annotated_demo_video
from services.violation_reasoning.service import evaluate_violations
from services.violation_reasoning.temporal import (
    evaluate_video_violations,
    vehicle_labels_from_records,
    violations_by_track,
)

from services.common.utils import center_of_bbox, iou





def _emit(job_id: str, event: str, data: dict | None = None) -> None:

    job_events.emit(job_id, event, data)





def _best_plate(plates: dict[str, PlateResult]) -> Optional[PlateResult]:

    valid = [p for p in plates.values() if p.plate_valid]

    if not valid:

        return None

    return max(valid, key=lambda p: p.ocr_confidence)





def _read_image(path: Path) -> np.ndarray:

    image = cv2.imread(str(path))

    if image is None:

        raise ValueError(f"Unable to read image: {path}")

    return image





def _extract_video_frames(
    path: Path,
    sample_every: int | None = None,
    max_frames: int | None = None,
) -> list[np.ndarray]:
    """Sample frames spread across the full clip (not only from the start)."""
    stride = sample_every if sample_every is not None else settings.video_sample_every
    limit = max_frames if max_frames is not None else settings.video_max_frames

    cap = cv2.VideoCapture(str(path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    if total > 0:
        if total <= limit:
            indices = list(range(0, total, max(1, stride)))[:limit]
        else:
            step = total / limit
            indices = [min(int(i * step), total - 1) for i in range(limit)]
        frames: list[np.ndarray] = []
        for fi in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
            ok, frame = cap.read()
            if ok:
                frames.append(frame)
        cap.release()
        if frames:
            return frames

    # Fallback: sequential read when metadata is missing
    cap = cv2.VideoCapture(str(path))
    frames = []
    idx = 0
    while cap.isOpened() and len(frames) < limit:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % stride == 0:
            frames.append(frame)
        idx += 1
    cap.release()

    if not frames:
        raise ValueError("No frames extracted from video")
    return frames





def _plate_distance_to_vehicle(plate_bbox: list[float], vehicle_bbox: list[float]) -> float:

    pcx, pcy = center_of_bbox(plate_bbox)

    vx1, vy1, vx2, vy2 = vehicle_bbox

    if vx1 <= pcx <= vx2 and vy1 <= pcy <= vy2:

        return 0.0

    dx = max(vx1 - pcx, 0.0, pcx - vx2)

    dy = max(vy1 - pcy, 0.0, pcy - vy2)

    return (dx * dx + dy * dy) ** 0.5





def _plates_for_vehicles(image: np.ndarray, vehicles) -> dict[str, PlateResult]:

    """Per-vehicle OCR with overlap-based global plate association."""

    plates: dict[str, PlateResult] = {}

    for vehicle in vehicles:

        plate = extract_plate_from_vehicle(image, vehicle.bbox, vehicle_class=vehicle.vehicle_type)

        plates[vehicle.vehicle_id] = plate

        plates[vehicle.track_id] = plate



    global_plates = find_plates_in_image(image)

    for gplate in global_plates:

        if not gplate.plate_valid:

            continue

        gbbox = getattr(gplate, "bbox", None)

        best_vid = None

        best_score = -1.0

        for vehicle in vehicles:

            if gbbox:

                score = iou(gbbox, vehicle.bbox)

                if score < 0.05:

                    dist = _plate_distance_to_vehicle(gbbox, vehicle.bbox)

                    score = max(0.0, 1.0 - dist / 200.0)

            else:

                score = 0.3

            existing = plates.get(vehicle.vehicle_id)

            if existing and existing.plate_valid and existing.ocr_confidence >= gplate.ocr_confidence:

                continue

            if score > best_score:

                best_score = score

                best_vid = vehicle.vehicle_id

        if best_vid and best_score > 0.1:

            vehicle = next(v for v in vehicles if v.vehicle_id == best_vid)

            plates[best_vid] = gplate

            plates[vehicle.track_id] = gplate



    return plates





def _build_temporal_evidence(tracked: list[list], vehicles) -> dict:

    """Summarize motion vectors for video jobs."""

    tracks_out = []

    for vehicle in vehicles:

        dx, dy = displacement_vector(tracked, vehicle.track_id)

        if abs(dx) + abs(dy) < 5:

            continue

        frame_indices = []

        for idx, frame in enumerate(tracked):

            for det in frame:

                if det.track_id == vehicle.track_id:

                    frame_indices.append(idx)

                    break

        tracks_out.append(

            {

                "vehicle_id": vehicle.vehicle_id,

                "track_id": vehicle.track_id,

                "displacement": [round(dx, 2), round(dy, 2)],

                "frames": frame_indices,

            }

        )

    return {"tracks": tracks_out}





def process_media_job(

    db: Session,

    media_row: Media,

    scene_config: Optional[SceneConfig] = None,

    job_id: Optional[str] = None,

    progress_callback: Optional[Callable[[str, dict], None]] = None,

) -> JobStatusResponse:

    job_id = job_id or str(uuid.uuid4())



    def progress(event: str, data: dict | None = None) -> None:

        _emit(job_id, event, data)

        if progress_callback:

            progress_callback(event, data or {})



    started = time.perf_counter()

    job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()

    if job:

        job.status = "processing"

        job.error_message = None

    else:

        job = ProcessingJob(

            job_id=job_id,

            media_id=media_row.media_id,

            status="processing",

            created_at=datetime.now(timezone.utc).isoformat(),

        )

        db.add(job)

    db.commit()



    try:

        path = Path(media_row.stored_path)

        scene = scene_config or SceneConfig()

        tracked = None

        temporal_evidence: dict = {}

        raw_frames: list[np.ndarray] | None = None

        processed_frames: list[np.ndarray] | None = None

        annotated_video_path = ""

        original_image = None


        progress("ingestion_started", {"media_id": media_row.media_id})



        if media_row.media_type == "video":

            raw_frames = _extract_video_frames(path)

            processed_frames = []

            preprocessing = None

            for frame in raw_frames:

                proc, meta = preprocess_frame(frame)

                processed_frames.append(proc)

                preprocessing = meta

            progress("preprocessing_done", {"frames": len(processed_frames)})



            frame_detections = [detect_objects(f) for f in processed_frames]

            tracked = track_detections(frame_detections)

            mid = len(processed_frames) // 2

            image = processed_frames[mid]

            detections = tracked[mid] if tracked else frame_detections[mid]

            if preprocessing is None:

                _, preprocessing, _ = preprocess_image(image, media_row.media_id)

            else:

                _, _, out_path = preprocess_image(image, media_row.media_id)

        else:

            original_image = _read_image(path)

            raw_frames = None

            processed_image, preprocessing, _ = preprocess_image(original_image, media_row.media_id)

            image = processed_image

            progress("preprocessing_done", {})

            detections = detect_objects(image)



        progress("detection_done", {"count": len(detections)})



        all_detections_for_congestion = detections

        if tracked:

            for frame in tracked:

                all_detections_for_congestion = frame



        congestion: CongestionResult = classify_congestion(detections, image.shape)



        source_image = original_image if raw_frames is None else None

        if tracked and raw_frames is not None and processed_frames is not None and preprocessing is not None:

            violations, vehicles, derived = evaluate_video_violations(

                raw_frames,

                processed_frames,

                tracked,

                preprocessing,

                scene,

            )

        else:

            violations, vehicles, derived = evaluate_violations(

                image,

                detections,

                preprocessing,

                scene=scene,

                frame_tracks=tracked,

                source_image=source_image,

            )



        if tracked:

            temporal_evidence = _build_temporal_evidence(tracked, vehicles)



        if tracked and raw_frames is not None and processed_frames is not None:

            vlabels = vehicle_labels_from_records(vehicles)

            vby_track = violations_by_track(violations)

            annotated_video_path = write_annotated_demo_video(

                raw_frames,

                tracked,

                media_row.media_id,

                vlabels,

                vby_track,

                len(violations),

            )

            progress("video_rendered", {"path": annotated_video_path})



        progress("violations_evaluated", {"violations": len(violations), "vehicles": len(vehicles)})



        plates_by_vehicle = _plates_for_vehicles(image, vehicles)

        best_plate = _best_plate(plates_by_vehicle)

        for violation in violations:

            plate = plates_by_vehicle.get(violation.vehicle_id) or best_plate

            if plate:

                violation.plate = plate



        captured_at = media_row.captured_at or datetime.now(timezone.utc).isoformat()

        enforcement, annotated_path = build_enforcement_result(

            media_id=media_row.media_id,

            job_id=job_id,

            image=image,

            vehicles=vehicles,

            violations=violations,

            detections=detections,

            derived=derived,

            preprocessing=preprocessing,

            plates_by_vehicle=plates_by_vehicle,

            captured_at=captured_at,

            congestion=congestion,

            temporal_evidence=temporal_evidence,

            annotated_video_path=annotated_video_path,

        )



        packages = build_evidence_packages(

            media_id=media_row.media_id,

            image=image,

            vehicles=vehicles,

            violations=violations,

            preprocessing=preprocessing,

            latitude=media_row.latitude,

            longitude=media_row.longitude,

            camera_id=media_row.camera_id,

            captured_at=captured_at,

            plates_by_vehicle=plates_by_vehicle,

            annotated_path=annotated_path,

        )



        for package in packages:

            plate = plates_by_vehicle.get(package.vehicle.get("vehicle_id", "")) or best_plate

            conf = package.violation.get("confidence", 0.0)

            if package.violation.get("type") == "none":

                review_status, review_tier = "auto_cleared", "low"

            else:

                review_status, review_tier = classify_review_tier(conf)

                package.review_status = review_status



            db.add(

                Evidence(

                    evidence_id=package.evidence_id,

                    media_id=package.media_id,

                    job_id=job_id,

                    violation_type=package.violation["type"],

                    confidence=package.violation["confidence"],

                    reason=package.violation["reason"],

                    plate_raw=plate.plate_raw if plate else None,

                    plate_normalized=plate.plate_normalized if plate else None,

                    plate_valid=1 if plate and plate.plate_valid else 0,

                    vehicle_class=package.vehicle.get("class"),

                    track_id=package.vehicle.get("track_id"),

                    vehicle_id=package.vehicle.get("vehicle_id"),

                    latitude=media_row.latitude,

                    longitude=media_row.longitude,

                    camera_id=media_row.camera_id,

                    evidence_bboxes=json.dumps(package.violation.get("evidence_bboxes", [])),

                    preprocessing_json=json.dumps(package.preprocessing),

                    annotated_path=package.annotated_path,

                    review_status=review_status,

                    review_tier=review_tier,

                    created_at=package.timestamp,

                )

            )



        save_congestion_snapshot(

            db,

            job_id=job_id,

            media_id=media_row.media_id,

            camera_id=media_row.camera_id,

            congestion=congestion.model_dump(),

        )



        latency_ms = (time.perf_counter() - started) * 1000.0

        job.status = "completed"

        job.latency_ms = round(latency_ms, 2)

        job.congestion_json = json.dumps(congestion.model_dump())

        job.completed_at = datetime.now(timezone.utc).isoformat()

        db.commit()



        progress("completed", {"latency_ms": job.latency_ms, "congestion": congestion.congestion_level})



        return JobStatusResponse(

            job_id=job_id,

            media_id=media_row.media_id,

            status="completed",

            latency_ms=job.latency_ms,

            evidence=packages,

            enforcement=enforcement,

            detections=detections + derived,

            preprocessing=preprocessing,

            annotated_path=annotated_path,

            annotated_video_path=annotated_video_path or None,

            congestion=congestion,

        )

    except Exception as exc:

        job.status = "failed"

        job.error_message = str(exc)

        job.completed_at = datetime.now(timezone.utc).isoformat()

        db.commit()

        progress("failed", {"error": str(exc)})

        return JobStatusResponse(

            job_id=job_id,

            media_id=media_row.media_id,

            status="failed",

            error_message=str(exc),

        )

