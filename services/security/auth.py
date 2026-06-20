"""Optional JWT / API-key authentication."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from config import settings

_bearer = HTTPBearer(auto_error=False)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

ROLE_HIERARCHY = {"viewer": 0, "constable": 1, "inspector": 2, "admin": 3}


def create_access_token(subject: str, role: str = "constable") -> str:
    try:
        import jwt
    except ImportError as exc:
        raise RuntimeError("PyJWT required for token creation") from exc

    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        import jwt
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="PyJWT not installed") from exc

    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_bearer),
    api_key: Optional[str] = Security(_api_key_header),
) -> Optional[dict]:
    """Returns user dict or None when auth is disabled."""
    if not settings.auth_enabled:
        return {"sub": "anonymous", "role": "admin"}

    if api_key and api_key == settings.api_key:
        return {"sub": "api_key_user", "role": "admin"}

    if credentials and credentials.credentials:
        payload = decode_token(credentials.credentials)
        return {"sub": payload.get("sub", "unknown"), "role": payload.get("role", "viewer")}

    if settings.auth_required:
        raise HTTPException(status_code=401, detail="Authentication required")
    return {"sub": "anonymous", "role": "viewer"}


def require_role(min_role: str):
    def _dep(user: Optional[dict] = Depends(get_current_user)) -> dict:
        user = user or {"sub": "anonymous", "role": "viewer"}
        if ROLE_HIERARCHY.get(user.get("role", "viewer"), 0) < ROLE_HIERARCHY.get(min_role, 99):
            raise HTTPException(status_code=403, detail=f"Requires {min_role} role")
        return user

    return _dep
