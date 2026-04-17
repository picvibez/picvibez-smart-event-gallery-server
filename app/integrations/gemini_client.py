from __future__ import annotations

from functools import lru_cache

from google import genai

from app.core.config import get_settings


@lru_cache
def get_gemini_client() -> genai.Client:
    settings = get_settings()
    return genai.Client(api_key=settings.GEMINI_API_KEY)
