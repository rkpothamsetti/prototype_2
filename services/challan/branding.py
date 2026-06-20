"""Nigha AI branding assets for printable receipts."""
from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOGO_CANDIDATES = (
    ROOT / "frontend" / "public" / "nigha-logo.png",
    ROOT / "frontend" / "dist" / "nigha-logo.png",
)


@lru_cache(maxsize=1)
def nigha_logo_data_uri() -> str:
    """Embed logo as data URI so saved HTML receipts work offline."""
    for path in LOGO_CANDIDATES:
        if path.is_file():
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            return f"data:image/png;base64,{encoded}"
    return ""
