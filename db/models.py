"""ORM models."""
from sqlalchemy import Column, Float, Integer, String, Text

from db.database import Base


class Media(Base):
    __tablename__ = "media"

    media_id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    media_type = Column(String, nullable=False)
    stored_path = Column(String, nullable=False)
    captured_at = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    camera_id = Column(String)
    created_at = Column(String, nullable=False)


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    job_id = Column(String, primary_key=True)
    media_id = Column(String, nullable=False)
    status = Column(String, nullable=False, default="queued")
    error_message = Column(Text)
    latency_ms = Column(Float)
    congestion_json = Column(Text)
    queue_backend = Column(String, default="inline")
    created_at = Column(String, nullable=False)
    completed_at = Column(String)


class Evidence(Base):
    __tablename__ = "evidence"

    evidence_id = Column(String, primary_key=True)
    media_id = Column(String, nullable=False)
    job_id = Column(String)
    violation_type = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    plate_raw = Column(String)
    plate_normalized = Column(String)
    plate_valid = Column(Integer, default=0)
    vehicle_class = Column(String)
    track_id = Column(String)
    vehicle_id = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    camera_id = Column(String)
    evidence_bboxes = Column(Text)
    preprocessing_json = Column(Text)
    annotated_path = Column(String)
    review_status = Column(String, nullable=False, default="pending_review")
    review_tier = Column(String, default="standard")
    created_at = Column(String, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id = Column(String, primary_key=True)
    evidence_id = Column(String, nullable=False)
    officer_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    details = Column(Text)
    created_at = Column(String, nullable=False)


class FeedbackSample(Base):
    __tablename__ = "feedback_samples"

    sample_id = Column(String, primary_key=True)
    evidence_id = Column(String, nullable=False)
    violation_type = Column(String, nullable=False)
    verdict = Column(String, nullable=False)
    meta_path = Column(String)
    created_at = Column(String, nullable=False)


class CongestionSnapshot(Base):
    __tablename__ = "congestion_snapshots"

    snapshot_id = Column(String, primary_key=True)
    job_id = Column(String, nullable=False)
    media_id = Column(String, nullable=False)
    camera_id = Column(String)
    congestion_level = Column(String, nullable=False)
    vehicle_count = Column(Integer, default=0)
    density_score = Column(Float, default=0.0)
    snapshot_json = Column(Text)
    created_at = Column(String, nullable=False)
