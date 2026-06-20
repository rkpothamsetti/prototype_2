"""Batch-process images from a directory (hackathon dataset ingest)."""
from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db.database import SessionLocal, init_db
from db.models import Media, ProcessingJob
from schemas import SceneConfig
from services.pipeline import process_media_job

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


def _resolve_input_dir(path: Path) -> Path:
    if path.is_absolute():
        return path
    return (ROOT / path).resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch process traffic images or videos")
    parser.add_argument(
        "input_dir",
        type=Path,
        nargs="?",
        default=Path("data/gridlock_dataset"),
        help="Directory of images or videos (default: data/gridlock_dataset)",
    )
    parser.add_argument("--videos", action="store_true", help="Process video files instead of images")
    parser.add_argument("--camera-id", default="CAM_BLR_MG_01")
    parser.add_argument("--lat", type=float, default=12.975)
    parser.add_argument("--lng", type=float, default=77.6063)
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    input_dir = _resolve_input_dir(args.input_dir)
    if not input_dir.exists():
        print(f"Error: input folder not found: {input_dir}")
        print()
        print("Stage images first, then batch-process:")
        print("  python scripts/load_gridlock_dataset.py <path-to-hackathon-dataset>")
        print("  python scripts/load_gridlock_dataset.py --demo   # no official dataset yet")
        print(f"  python scripts/batch_process.py {input_dir}")
        sys.exit(1)

    init_db()
    db = SessionLocal()
    processed = 0

    exts = VIDEO_EXTS if args.videos else IMAGE_EXTS
    media_type = "video" if args.videos else "image"

    files = sorted(p for p in input_dir.iterdir() if p.suffix.lower() in exts)[: args.limit]
    if not files:
        print(f"No {'videos' if args.videos else 'images'} found in {input_dir}")
        print("Supported extensions:", ", ".join(sorted(exts)))
        sys.exit(1)

    from services.warmup import warmup_all

    print("Warming up models (one-time)...")
    warmup_all()

    for src in files:
        media_id = str(uuid.uuid4())
        dest = ROOT / "data" / "uploads" / f"{media_id}{src.suffix}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(src.read_bytes())

        media = Media(
            media_id=media_id,
            filename=src.name,
            media_type=media_type,
            stored_path=str(dest),
            captured_at=datetime.now(timezone.utc).isoformat(),
            latitude=args.lat,
            longitude=args.lng,
            camera_id=args.camera_id,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        db.add(media)
        job_id = f"job-{media_id[:8]}"
        db.add(
            ProcessingJob(
                job_id=job_id,
                media_id=media_id,
                status="queued",
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        db.commit()

        result = process_media_job(db, media, scene_config=SceneConfig(), job_id=job_id)
        print(f"{src.name} -> {result.status} ({result.latency_ms}ms)")
        processed += 1

    db.close()
    print(f"Processed {processed} {media_type} files")


if __name__ == "__main__":
    main()
