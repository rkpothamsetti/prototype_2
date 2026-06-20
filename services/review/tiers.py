"""Confidence-tier routing for officer review queue."""
from __future__ import annotations

from config import settings


def classify_review_tier(confidence: float) -> tuple[str, str]:
    """
    Returns (review_status, review_tier).
    - auto_cleared: below low threshold
    - pending_review + fast_track: high confidence
    - pending_review + standard: mid confidence
    """
    low = settings.confidence_tier_low
    high = settings.confidence_tier_high

    if confidence < low:
        return "auto_cleared", "low"
    if confidence >= high:
        return "pending_review", "fast_track"
    return "pending_review", "standard"
