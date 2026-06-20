#!/usr/bin/env python3
"""Run a local video enforcement demo on an MP4 clip (no server required)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import settings
from schemas import SceneConfig
from services.detection.service import detect_objects
from services.evidence.video import write_annotated_demo_video
from services.pipeline import _extract_video_frames
from services.preprocessing.service import preprocess_frame
from services.tracking.service import track_detections
from services.violation_reasoning.temporal import (
    evaluate_video_violations,
    vehicle_labels_from_records,
    violations_by_track,
)


def _extract_frames(path: Path, sample_every: int | None = None, max_frames: int | None = None) -> list:
    try:
        return _extract_video_frames(path, sample_every=sample_every, max_frames=max_frames)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Nigha AI video clip demo")
    parser.add_argument("video", type=Path, help="Path to MP4/video clip")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Output MP4 path")
    parser.add_argument(
        "--sample-every",
        type=int,
        default=None,
        help=f"Frame stride (default: {settings.video_sample_every})",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help=f"Max sampled frames (default: {settings.video_max_frames})",
    )
    args = parser.parse_args()

    if not args.video.exists():
        raise SystemExit(f"File not found: {args.video}")

    print(f"Loading {args.video} ...")
    raw_frames = _extract_frames(args.video, sample_every=args.sample_every, max_frames=args.max_frames)
    processed = []
    meta = None
    for frame in raw_frames:
        proc, meta = preprocess_frame(frame)
        processed.append(proc)

    print(f"Detecting on {len(processed)} frames ...")
    frame_dets = [detect_objects(f) for f in processed]
    tracked = track_detections(frame_dets)

    print("Evaluating violations across frames ...")
    violations, vehicles, _ = evaluate_video_violations(
        raw_frames, processed, tracked, meta, SceneConfig()
    )

    media_id = args.video.stem[:32]
    out = write_annotated_demo_video(
        raw_frames,
        tracked,
        media_id,
        vehicle_labels_from_records(vehicles),
        violations_by_track(violations),
        len(violations),
    )
    if args.output:
        import shutil

        shutil.copy2(out, args.output)
        out = str(args.output)

    print(f"Violations: {len(violations)}")
    for v in violations:
        print(f"  - {v.vehicle_id} {v.violation_type} ({v.confidence:.0%})")
    print(f"Annotated demo video: {out}")


if __name__ == "__main__":
    main()
