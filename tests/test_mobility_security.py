"""Tests for mobility analytics and security paths."""
from pathlib import Path

import pytest
from fastapi import HTTPException

from services.analytics.mobility import get_mobility_analytics
from services.security.paths import resolve_under, safe_filename


def test_safe_filename_rejects_traversal():
    with pytest.raises(HTTPException):
        safe_filename("../../etc/passwd")


def test_resolve_under(tmp_path):
    base = tmp_path / "evidence"
    base.mkdir()
    f = base / "test.jpg"
    f.write_text("x")
    assert resolve_under(base, "test.jpg") == f.resolve()


def test_mobility_analytics_empty(db_session):
    result = get_mobility_analytics(db_session)
    assert result.zones == []
    assert result.congestion_violation_correlation == 0.0
