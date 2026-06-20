"""Safe filesystem path resolution."""
from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException


def safe_filename(filename: str) -> str:
    """Strip path components — prevent directory traversal."""
    name = Path(filename).name
    if not name or name in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if ".." in filename.replace("\\", "/"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return name


def resolve_under(base_dir: Path, filename: str) -> Path:
    name = safe_filename(filename)
    path = (base_dir / name).resolve()
    base = base_dir.resolve()
    if not str(path).startswith(str(base)):
        raise HTTPException(status_code=403, detail="Access denied")
    return path
