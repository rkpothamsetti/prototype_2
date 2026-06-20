"""Seed demo database with hero images for zero-wait hackathon pitch."""
from __future__ import annotations

import argparse
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db.database import SessionLocal, init_db
from db.models import Evidence, Media, ProcessingJob
from schemas import SceneConfig
from services.pipeline import process_media_job

HERO_DIR = ROOT / "data" / "demo_hero"
SAMPLE_DIR = ROOT / "CONTEXT" / "examples" / "sample_input"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _ensure_hero_images() -> list[Path]:
    from scripts.generate_hero_images import generate_hero_images

    existing = sorted(p for p in HERO_DIR.glob("*") if p.suffix.lower() in IMAGE_EXTS)
    if len(existing) >= 3:
        return existing
    generate_hero_images()
    return sorted(p for p in HERO_DIR.glob("*") if p.suffix.lower() in IMAGE_EXTS)


def _ensure_samples() -> None:
    if not any(SAMPLE_DIR.glob("*.jpg")):
        from scripts.generate_samples import generate_samples

        generate_samples()


def _process_file(
    db,
    src: Path,
    *,
    camera_id: str = "CAM_BLR_MG_01",
    lat: float = 12.975,
    lng: float = 77.6063,
    auto_confirm: bool = False,
) -> str | None:
    media_id = str(uuid.uuid4())
    dest = ROOT / "data" / "uploads" / f"{media_id}{src.suffix}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)

    now = datetime.now(timezone.utc).isoformat()
    media = Media(
        media_id=media_id,
        filename=src.name,
        media_type="image",
        stored_path=str(dest),
        captured_at=now,
        latitude=lat,
        longitude=lng,
        camera_id=camera_id,
        created_at=now,
    )
    db.add(media)
    job_id = f"job-{media_id[:8]}"
    db.add(
        ProcessingJob(
            job_id=job_id,
            media_id=media_id,
            status="queued",
            created_at=now,
        )
    )
    db.commit()

    result = process_media_job(db, media, scene_config=SceneConfig(), job_id=job_id)
    print(f"  {src.name} -> {result.status} ({result.latency_ms}ms)")

    if auto_confirm and result.status == "completed":
        rows = (
            db.query(Evidence)
            .filter(Evidence.media_id == media_id, Evidence.violation_type != "none")
            .all()
        )
        for row in rows:
            if row.plate_valid or row.confidence >= 0.55:
                row.review_status = "confirmed"
        db.commit()

    return job_id if result.status == "completed" else None


def seed_demo(*, include_samples: bool = True, limit: int = 8) -> dict:
    from services.warmup import warmup_all

    print("Warming up models (one-time, ~30-60s)...")
    warmup_all()

    init_db()
    db = SessionLocal()
    processed = 0
    confirmed = 0

    try:
        hero_files = _ensure_hero_images()[:limit]
        print(f"Processing {len(hero_files)} hero images...")
        for i, src in enumerate(hero_files):
            cam = ["CAM_BLR_MG_01", "CAM_BLR_SILK_01", "CAM_BLR_HEBBAL_01"][i % 3]
            if _process_file(db, src, camera_id=cam, auto_confirm=True):
                processed += 1

        if include_samples:
            _ensure_samples()
            sample_files = sorted(SAMPLE_DIR.glob("*.jpg"))[: max(0, limit - len(hero_files))]
            if sample_files:
                print(f"Processing {len(sample_files)} sample images...")
            for src in sample_files:
                if _process_file(db, src, auto_confirm=False):
                    processed += 1

        confirmed = db.query(Evidence).filter(Evidence.review_status == "confirmed").count()
        pending = db.query(Evidence).filter(Evidence.review_status == "pending_review").count()
        with_plates = db.query(Evidence).filter(Evidence.plate_valid == True).count()  # noqa: E712

        summary = {
            "hero_images": len(hero_files),
            "jobs_completed": processed,
            "confirmed_evidence": confirmed,
            "pending_review": pending,
            "valid_plates": with_plates,
        }
        print("\n=== Demo seed complete ===")
        for k, v in summary.items():
            print(f"  {k}: {v}")
        return summary
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo DB with hero traffic images")
    parser.add_argument("--no-samples", action="store_true", help="Skip CONTEXT sample images")
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()
    seed_demo(include_samples=not args.no_samples, limit=args.limit)


if __name__ == "__main__":
    main()
