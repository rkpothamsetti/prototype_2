"""Tests for model warmup."""
from __future__ import annotations

import numpy as np
from unittest.mock import MagicMock, patch


def test_warmup_status_before_load():
    import services.warmup as warmup

    warmup._ready = False
    warmup._warming = False
    warmup._error = None
    warmup._models = []
    status = warmup.get_status()
    assert status["ready"] is False
    assert status["warming"] is False


def test_warmup_marks_ready_on_success():
    import services.warmup as warmup

    warmup._ready = False
    warmup._warming = False
    dummy_model = MagicMock()
    dummy_reader = MagicMock()
    dummy_reader.readtext.return_value = []

    with patch("services.detection.service._load_model", return_value=dummy_model):
        with patch("services.detection.service.detect_objects", return_value=[]):
            with patch("services.ocr.service._load_ocr", return_value=dummy_reader):
                with patch("services.detection.helmet_yolo.resolve_helmet_model_path", return_value=None):
                    warmup.warmup_all()

    assert warmup.is_ready() is True
    assert "yolo11" in warmup.get_status()["models"]
