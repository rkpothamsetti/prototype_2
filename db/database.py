"""SQLAlchemy database setup."""
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import DB_PATH, ROOT_DIR, ensure_dirs, settings


class Base(DeclarativeBase):
    pass


ensure_dirs()


def _build_engine():
    if settings.database_url:
        return create_engine(settings.database_url, pool_pre_ping=True)
    return create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    from db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_columns(engine)
    schema_path = ROOT_DIR / "CONTEXT" / "data_schema.sql"
    if schema_path.exists():
        with engine.connect() as conn:
            for statement in schema_path.read_text(encoding="utf-8").split(";"):
                stmt = statement.strip()
                if stmt:
                    try:
                        conn.execute(text(stmt))
                    except Exception:
                        pass
            conn.commit()


def _migrate_columns(eng) -> None:
    """Add columns introduced after initial schema without breaking existing DBs."""
    migrations = [
        ("evidence", "vehicle_id", "TEXT"),
        ("evidence", "review_tier", "TEXT DEFAULT 'standard'"),
        ("processing_jobs", "congestion_json", "TEXT"),
        ("processing_jobs", "queue_backend", "TEXT DEFAULT 'inline'"),
    ]
    with eng.connect() as conn:
        for table, column, col_type in migrations:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                conn.commit()
            except Exception:
                pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
