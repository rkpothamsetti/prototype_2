"""Download dedicated helmet YOLO weights (iam-tsr/yolov8n-helmet-detection)."""
from __future__ import annotations

import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "data" / "models"
DEST = MODELS_DIR / "helmet_yolo.pt"

HF_URL = "https://huggingface.co/iam-tsr/yolov8n-helmet-detection/resolve/main/best.pt"


def download(dest: Path = DEST, url: str = HF_URL) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 1_000_000:
        print(f"Already present: {dest} ({dest.stat().st_size // 1024} KB)")
        return dest

    print(f"Downloading helmet YOLO from {url} ...")
    with httpx.stream("GET", url, follow_redirects=True, timeout=120.0) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        written = 0
        with open(dest, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=65536):
                f.write(chunk)
                written += len(chunk)
                if total:
                    pct = 100 * written / total
                    print(f"\r  {written // 1024} / {total // 1024} KB ({pct:.0f}%)", end="")
    print(f"\nSaved to {dest}")
    return dest


if __name__ == "__main__":
    try:
        download()
    except Exception as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        sys.exit(1)
