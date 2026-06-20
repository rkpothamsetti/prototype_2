"""Copy hackathon dataset images into data/gridlock_dataset for batch processing."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEFAULT_OUT = ROOT / "data" / "gridlock_dataset"
DEMO_SOURCES = [
    ROOT / "data" / "demo_hero",
    ROOT / "CONTEXT" / "examples" / "sample_input",
    ROOT / "data" / "test_media" / "images",
]

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".mp4", ".avi", ".mov"}


def _stage_from_dir(source: Path, output: Path, limit: int, seen: set[str]) -> int:
    added = 0
    if not source.exists():
        return 0
    for path in sorted(source.rglob("*")):
        if path.suffix.lower() not in IMAGE_EXTS:
            continue
        if path.name in seen:
            continue
        dest = output / path.name
        if not dest.exists():
            shutil.copy2(path, dest)
        seen.add(path.name)
        added += 1
        if added >= limit:
            break
    return added


def stage_demo(output: Path, limit: int = 100) -> int:
    """Bootstrap gridlock_dataset from bundled demo/hero images when no official data yet."""
    from scripts.generate_hero_images import generate_hero_images
    from scripts.generate_samples import generate_samples

    if not any(output.glob("*")):
        output.mkdir(parents=True, exist_ok=True)

    if not any((ROOT / "data" / "demo_hero").glob("*")):
        generate_hero_images()
    if not any((ROOT / "CONTEXT" / "examples" / "sample_input").glob("*.jpg")):
        generate_samples()

    seen: set[str] = set()
    total = 0
    for source in DEMO_SOURCES:
        remaining = max(0, limit - total)
        if remaining == 0:
            break
        n = _stage_from_dir(source, output, remaining, seen)
        total += n
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="Load Gridlock dataset into project data folder")
    parser.add_argument(
        "source_dir",
        type=Path,
        nargs="?",
        help="Hackathon dataset directory (optional if --demo)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Use bundled hero + sample images when official BTP/ASTraM data is not available",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    if args.demo or args.source_dir is None:
        count = stage_demo(args.output, args.limit)
        print(f"Staged {count} demo files in {args.output}")
        print(f"Run: python scripts/batch_process.py {args.output}")
        return

    source = args.source_dir if args.source_dir.is_absolute() else (ROOT / args.source_dir).resolve()
    if not source.exists():
        print(f"Source not found: {source}")
        print("Use --demo to bootstrap from bundled hero images:")
        print("  python scripts/load_gridlock_dataset.py --demo")
        sys.exit(1)

    seen: set[str] = set()
    count = _stage_from_dir(source, args.output, args.limit, seen)
    print(f"Staged {count} files in {args.output}")
    print(f"Run: python scripts/batch_process.py {args.output}")


if __name__ == "__main__":
    main()
