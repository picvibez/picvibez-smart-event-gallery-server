from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import get_settings

ALGORITHM = "HS256"


def decode_supabase_jwt(token: str) -> dict[str, Any]:
    """Decode and validate a Supabase-issued JWT.

    Returns the full payload on success.
    Raises HTTPException 401 on any failure.
    """
    settings = get_settings()
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=[ALGORITHM],
            audience="authenticated",
        )
    except JWTError:
        raise credentials_exc

    exp = payload.get("exp")
    if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(tz=timezone.utc):
        raise credentials_exc

    sub = payload.get("sub")
    if not sub:
        raise credentials_exc

    return payload
