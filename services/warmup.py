"""Preload CV models at startup so first upload is fast."""
from __future__ import annotations

import logging
import threading
from typing import Any

import cv2
import numpy as np

_log = logging.getLogger(__name__)

_lock = threading.Lock()
_ready = False
_warming = False
_error: str | None = None
_models: list[str] = []


def is_ready() -> bool:
    with _lock:
        return _ready


def get_status() -> dict[str, Any]:
    with _lock:
        return {
            "ready": _ready,
            "warming": _warming,
            "error": _error,
            "models": list(_models),
        }


def warmup_all() -> None:
    """Load YOLO, OCR, and optional helmet model; run one dummy inference each."""
    global _ready, _warming, _error, _models

    with _lock:
        if _ready or _warming:
            return
        _warming = True
        _error = None

    loaded: list[str] = []
    try:
        dummy = np.full((640, 640, 3), 90, dtype=np.uint8)
        cv2.rectangle(dummy, (120, 200), (520, 480), (40, 40, 200), -1)
        cv2.rectangle(dummy, (280, 420), (420, 470), (255, 255, 255), -1)
        cv2.putText(dummy, "KA01AB1234", (290, 455), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)

        from services.detection.service import _load_model, detect_objects

        _load_model()
        loaded.append("yolo11")
        detect_objects(dummy)

        from services.ocr.service import _load_ocr

        reader = _load_ocr()
        loaded.append("easyocr")
        reader.readtext(dummy, detail=0)

        try:
            from services.detection.helmet_yolo import _load_helmet_model, resolve_helmet_model_path

            if resolve_helmet_model_path():
                _load_helmet_model()
                loaded.append("helmet_yolo")
        except Exception as exc:
            _log.debug("Helmet YOLO warmup skipped: %s", exc)

        with _lock:
            _models = loaded
            _ready = True
            _error = None
        _log.info("Model warmup complete: %s", ", ".join(loaded))
    except Exception as exc:
        _log.warning("Model warmup failed: %s", exc)
        with _lock:
            _error = str(exc)
            _models = loaded
    finally:
        with _lock:
            _warming = False


def start_warmup_background() -> None:
    threading.Thread(target=warmup_all, daemon=True, name="nigha-warmup").start()
