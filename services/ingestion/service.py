"""Media ingestion service."""
from __future__ import annotations

import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import cv2
from fastapi import UploadFile

from config import UPLOAD_DIR, settings


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/jpg", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/avi", "video/quicktime", "video/x-msvideo"}
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES


def _guess_mime(filename: str, content_type: Optional[str]) -> str:
    if content_type and content_type != "application/octet-stream":
        return content_type
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def _extract_exif_timestamp(path: Path) -> Optional[str]:
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        with Image.open(path) as img:
            exif = img._getexif() or {}
            for tag_id, value in exif.items():
                if TAGS.get(tag_id) == "DateTimeOriginal":
                    dt = datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
                    return dt.replace(tzinfo=timezone.utc).isoformat()
    except Exception:
        return None
    return None


async def save_upload(
    file: UploadFile,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    camera_id: Optional[str] = None,
) -> dict:
    mime = _guess_mime(file.filename or "upload.jpg", file.content_type)
    if mime not in ALLOWED_TYPES:
        raise ValueError(f"Unsupported file type: {mime}")

    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise ValueError(f"File exceeds {settings.max_upload_mb}MB limit")

    media_id = str(uuid.uuid4())
    ext = Path(file.filename or "upload.jpg").suffix or ".jpg"
    stored_path = UPLOAD_DIR / f"{media_id}{ext}"
    stored_path.write_bytes(content)

    media_type = "video" if mime in ALLOWED_VIDEO_TYPES else "image"
    if media_type == "video":
        cap = cv2.VideoCapture(str(stored_path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        duration = frame_count / fps if fps > 0 else 0
        cap.release()
        if duration > settings.max_video_seconds:
            stored_path.unlink(missing_ok=True)
            raise ValueError(f"Video exceeds {settings.max_video_seconds}s limit")

    captured_at = _extract_exif_timestamp(stored_path) or datetime.now(timezone.utc).isoformat()

    return {
        "media_id": media_id,
        "filename": file.filename or stored_path.name,
        "media_type": media_type,
        "stored_path": str(stored_path),
        "captured_at": captured_at,
        "latitude": latitude,
        "longitude": longitude,
        "camera_id": camera_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
