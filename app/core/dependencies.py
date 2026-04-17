from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.core.security import decode_supabase_jwt
from app.integrations.supabase_client import get_supabase_client

_bearer = HTTPBearer(auto_error=False)


class CurrentUser:
    """Lightweight object representing the authenticated user."""

    __slots__ = ("id", "email", "role", "raw")

    def __init__(self, payload: dict) -> None:
        self.id: str = payload["sub"]
        self.email: str = payload.get("email", "")
        self.role: str = payload.get("role", "authenticated")
        self.raw: dict = payload


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_supabase_jwt(credentials.credentials)
    return CurrentUser(payload)


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> CurrentUser | None:
    """Same as get_current_user but returns None instead of 401."""
    if credentials is None:
        return None
    try:
        payload = decode_supabase_jwt(credentials.credentials)
        return CurrentUser(payload)
    except HTTPException:
        return None


def get_db():
    """Return the Supabase client (service-role) for DB operations."""
    return get_supabase_client()


def get_config() -> Settings:
    return get_settings()
