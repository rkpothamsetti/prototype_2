"""Shared Pydantic schemas."""
from typing import Any, Optional

from pydantic import BaseModel, Field


class BBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

    def as_list(self) -> list[float]:
        return [self.x1, self.y1, self.x2, self.y2]


class Detection(BaseModel):
    track_id: str
    class_name: str
    bbox: list[float]
    confidence: float
    role: Optional[str] = None


class PreprocessingMetadata(BaseModel):
    quality_score: float
    blur_variance: float
    night_detected: bool
    enhancements_applied: list[str] = Field(default_factory=list)
    original_size: list[int]
    processed_size: list[int]


class PlateResult(BaseModel):
    plate_raw: str = ""
    plate_normalized: str = ""
    plate_valid: bool = False
    ocr_confidence: float = 0.0
    plate_face: str = ""  # front | rear | unknown — whichever end was read


class ViolationRecord(BaseModel):
    violation_type: str
    confidence: float
    reason: str
    evidence_bboxes: list[list[float]] = Field(default_factory=list)
    vehicle_class: str = ""
    track_id: str = ""
    vehicle_id: str = ""
    plate: Optional[PlateResult] = None


class AssociatedPersonOut(BaseModel):
    person_id: str
    role: str
    bbox: list[float]
    confidence: float
    helmet_id: Optional[str] = None
    helmet_detected: bool = False
    proximity_score: float = 0.0


class VehicleEnforcementRecord(BaseModel):
    vehicle_id: str
    vehicle_type: str
    track_id: str
    bounding_box: list[float]
    license_plate: Optional[PlateResult] = None
    associated_persons: list[AssociatedPersonOut] = Field(default_factory=list)
    rider_count: int = 0
    violations: list[dict[str, Any]] = Field(default_factory=list)
    compliance_status: str = "compliant"  # compliant | violation
    confidence: float = 0.0


class CongestionResult(BaseModel):
    congestion_level: str = "moderate"
    vehicle_count: int = 0
    density_score: float = 0.0
    combined_score: float = 0.0
    confidence: float = 0.0


class EnforcementResult(BaseModel):
    media_id: str
    job_id: str
    timestamp: str
    vehicles: list[VehicleEnforcementRecord] = Field(default_factory=list)
    all_detections: list[Detection] = Field(default_factory=list)
    derived_objects: list[Detection] = Field(default_factory=list)
    annotated_path: str = ""
    annotated_video_path: str = ""
    preprocessing: dict[str, Any] = Field(default_factory=dict)
    congestion: Optional[CongestionResult] = None
    temporal_evidence: dict[str, Any] = Field(default_factory=dict)


class SceneConfig(BaseModel):
    legal_direction_angle: float = 0.0
    no_parking_zones: list[list[float]] = Field(default_factory=list)
    stop_line_y: Optional[float] = None
    intersection_roi: Optional[list[float]] = None
    traffic_light_state: str = "unknown"
    signal_state: str = "unknown"


class EvidencePackage(BaseModel):
    evidence_id: str
    media_id: str
    timestamp: str
    location: dict[str, Any]
    vehicle: dict[str, Any]
    violation: dict[str, Any]
    preprocessing: dict[str, Any]
    review_status: str = "pending_review"
    annotated_path: str = ""
    detections: list[Detection] = Field(default_factory=list)


class MediaUploadResponse(BaseModel):
    media_id: str
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    media_id: str
    status: str
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None
    evidence: list[EvidencePackage] = Field(default_factory=list)
    enforcement: Optional[EnforcementResult] = None
    detections: list[Detection] = Field(default_factory=list)
    preprocessing: Optional[PreprocessingMetadata] = None
    annotated_path: Optional[str] = None
    annotated_video_path: Optional[str] = None
    congestion: Optional[CongestionResult] = None
    queue_backend: Optional[str] = None


class EvidenceSearchParams(BaseModel):
    plate: Optional[str] = None
    violation_type: Optional[str] = None
    review_status: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    camera_id: Optional[str] = None
    violations_only: bool = False
    limit: int = 50
    offset: int = 0


class AnalyticsSummary(BaseModel):
    total_violations: int
    by_type: dict[str, int]
    by_review_status: dict[str, int]
    by_review_tier: dict[str, int] = Field(default_factory=dict)
    daily_trends: list[dict[str, Any]]
    hotspots: list[dict[str, Any]]
    repeat_offenders: list[dict[str, Any]]
    congestion_summary: dict[str, int] = Field(default_factory=dict)
    officer_load_reduction_pct: float = 0.0


class MobilityAnalytics(BaseModel):
    zones: list[dict[str, Any]] = Field(default_factory=list)
    peak_hours: list[dict[str, Any]] = Field(default_factory=list)
    congestion_violation_correlation: float = 0.0
    officer_load_reduction_pct: float = 0.0
    pending_review_count: int = 0
    avg_processing_ms: float = 0.0
    generated_at: str = ""


class FeedbackStats(BaseModel):
    pending_retrain: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)


class ChallanExportResponse(BaseModel):
    challan: dict[str, Any]
    evidence_id: str
    receipt_path: str = ""


class QueueStatusResponse(BaseModel):
    backend: str
    redis_connected: bool = False
    error: Optional[str] = None
    url: Optional[str] = None


class RTSPCaptureRequest(BaseModel):
    rtsp_url: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    camera_id: Optional[str] = None
    legal_direction_angle: float = 0.0


class MetricsResponse(BaseModel):
    latency_p50_ms: float
    latency_p95_ms: float
    throughput_ips: float
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
