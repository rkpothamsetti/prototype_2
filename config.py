"""Application configuration."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
PROCESSED_DIR = DATA_DIR / "processed"
EVIDENCE_DIR = DATA_DIR / "evidence"
FEEDBACK_DIR = DATA_DIR / "feedback"
DB_PATH = DATA_DIR / "trafficvision.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TV_")

    app_name: str = "Nigha AI"
    api_prefix: str = "/api/v1"
    max_upload_mb: int = 150
    max_video_seconds: int = 120
    video_sample_every: int = 5
    video_max_frames: int = 60
    yolo_model: str = "yolo11n.pt"
    yolo_confidence: float = 0.35
    use_helmet_yolo: bool = True
    helmet_yolo_model: str = "data/models/helmet_yolo.pt"
    helmet_yolo_confidence: float = 0.30
    preprocess_max_edge: int = 1280
    blur_threshold: float = 80.0
    api_port: int = 8001
    demo_fallback: bool = False
    serve_frontend: bool = False
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]
    # Allow Render / Vercel preview URLs in production (set empty to disable)
    cors_origin_regex: str = r"https://.*\.(onrender\.com|vercel\.app|ngrok-free\.app|ngrok\.io)"

    # Confidence-tier routing
    confidence_tier_low: float = 0.45
    confidence_tier_high: float = 0.80

    # Database — SQLite default; set TV_DATABASE_URL for PostgreSQL
    database_url: str = ""

    # Auth (optional — disabled by default for local dev)
    auth_enabled: bool = False
    auth_required: bool = False
    api_key: str = "nigha-demo-key"
    jwt_secret: str = "nigha-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # Job queue
    redis_url: str = ""
    redis_queue_name: str = "nigha_jobs"

    # RTSP
    rtsp_timeout_sec: int = 10

    # Rate limiting
    rate_limit_upload: str = "30/minute"

    # Startup — preload models so first upload is fast (disable in tests via TV_WARMUP_ENABLED=false)
    warmup_enabled: bool = True
    warmup_blocking: bool = True

    # Demo / eval paths
    demo_hero_dir: str = "data/demo_hero"
    eval_labels_dir: str = "data/eval/labels"


settings = Settings()


def ensure_dirs() -> None:
    for path in (DATA_DIR, UPLOAD_DIR, PROCESSED_DIR, EVIDENCE_DIR, FEEDBACK_DIR, DATA_DIR / "models"):
        path.mkdir(parents=True, exist_ok=True)
