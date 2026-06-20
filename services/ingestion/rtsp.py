"""RTSP frame capture stub for live CCTV ingest."""
from __future__ import annotations

from typing import Optional

import cv2
import numpy as np

from config import settings


def capture_rtsp_frame(rtsp_url: str, timeout_sec: Optional[int] = None) -> np.ndarray:
    """
    Capture a single frame from an RTSP stream.
    Raises ValueError if stream cannot be opened.
    """
    timeout = timeout_sec or settings.rtsp_timeout_sec
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        raise ValueError(f"Cannot open RTSP stream: {rtsp_url}")

    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    ok, frame = cap.read()
    cap.release()

    if not ok or frame is None:
        raise ValueError("Failed to read frame from RTSP stream")
    return frame


def sample_rtsp_clip(rtsp_url: str, max_frames: int = 10, sample_every: int = 5) -> list[np.ndarray]:
    """Sample frames from RTSP for short clip processing."""
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        raise ValueError(f"Cannot open RTSP stream: {rtsp_url}")

    frames: list[np.ndarray] = []
    idx = 0
    while cap.isOpened() and len(frames) < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % sample_every == 0:
            frames.append(frame)
        idx += 1
    cap.release()

    if not frames:
        raise ValueError("No frames captured from RTSP stream")
    return frames
