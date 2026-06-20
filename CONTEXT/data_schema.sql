-- TrafficVision AI SQLite schema

CREATE TABLE IF NOT EXISTS media (
    media_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    media_type TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    captured_at TEXT,
    latitude REAL,
    longitude REAL,
    camera_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS processing_jobs (
    job_id TEXT PRIMARY KEY,
    media_id TEXT NOT NULL REFERENCES media(media_id),
    status TEXT NOT NULL DEFAULT 'queued',
    error_message TEXT,
    latency_ms REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    media_id TEXT NOT NULL REFERENCES media(media_id),
    job_id TEXT REFERENCES processing_jobs(job_id),
    violation_type TEXT NOT NULL,
    confidence REAL NOT NULL,
    reason TEXT NOT NULL,
    plate_raw TEXT,
    plate_normalized TEXT,
    plate_valid INTEGER DEFAULT 0,
    vehicle_class TEXT,
    track_id TEXT,
    latitude REAL,
    longitude REAL,
    camera_id TEXT,
    evidence_bboxes TEXT,
    preprocessing_json TEXT,
    annotated_path TEXT,
    review_status TEXT NOT NULL DEFAULT 'pending_review',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_evidence_violation_type ON evidence(violation_type);
CREATE INDEX IF NOT EXISTS idx_evidence_plate ON evidence(plate_normalized);
CREATE INDEX IF NOT EXISTS idx_evidence_review ON evidence(review_status);
CREATE INDEX IF NOT EXISTS idx_evidence_created ON evidence(created_at);
