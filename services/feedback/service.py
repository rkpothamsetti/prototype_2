"""Active learning feedback from officer rejections."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from config import DATA_DIR, ensure_dirs
from db.models import Evidence, FeedbackSample

FEEDBACK_DIR = DATA_DIR / "feedback"


def record_rejection_feedback(db: Session, evidence: Evidence) -> FeedbackSample:
    """Queue rejected evidence for model retraining."""
    ensure_dirs()
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)

    sample_id = str(uuid.uuid4())
    meta = {
        "evidence_id": evidence.evidence_id,
        "violation_type": evidence.violation_type,
        "confidence": evidence.confidence,
        "annotated_path": evidence.annotated_path,
        "verdict": "rejected",
    }
    meta_path = FEEDBACK_DIR / f"{sample_id}.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    row = FeedbackSample(
        sample_id=sample_id,
        evidence_id=evidence.evidence_id,
        violation_type=evidence.violation_type,
        verdict="rejected",
        meta_path=str(meta_path),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(row)
    return row


def get_feedback_stats(db: Session) -> dict:
    rows = db.query(FeedbackSample).all()
    by_type: dict[str, int] = {}
    for row in rows:
        by_type[row.violation_type] = by_type.get(row.violation_type, 0) + 1
    return {
        "pending_retrain": len(rows),
        "by_type": by_type,
    }
