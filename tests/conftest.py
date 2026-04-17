from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch):
    """Set required env vars for tests."""
    env_vars = {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
        "SUPABASE_JWT_SECRET": "test-jwt-secret-at-least-32-chars-long!!",
        "AWS_ACCESS_KEY_ID": "AKIATEST",
        "AWS_SECRET_ACCESS_KEY": "test-secret",
        "AWS_REGION": "us-east-1",
        "S3_MEDIA_BUCKET": "test-bucket",
        "CLOUDFRONT_DOMAIN": "test.cloudfront.net",
        "APP_ENV": "testing",
        "CORS_ORIGINS": "http://localhost:3000",
    }
    for k, v in env_vars.items():
        monkeypatch.setenv(k, v)


@pytest.fixture
def mock_db():
    """Mock Supabase client."""
    db = MagicMock()
    return db


@pytest.fixture
def mock_s3():
    """Mock S3 client."""
    s3 = MagicMock()
    s3.generate_presigned_url.return_value = "https://test-bucket.s3.amazonaws.com/test-key?signed=1"
    return s3


@pytest.fixture
def test_user_payload():
    return {
        "sub": "test-user-id-123",
        "email": "test@example.com",
        "role": "authenticated",
        "aud": "authenticated",
        "exp": 9999999999,
    }


@pytest.fixture
def auth_token(test_user_payload):
    from jose import jwt

    return jwt.encode(test_user_payload, "test-jwt-secret-at-least-32-chars-long!!", algorithm="HS256")


@pytest.fixture
def client(mock_db, mock_s3):
    """Create a test client with mocked dependencies."""
    from app.core.config import get_settings

    get_settings.cache_clear()

    with (
        patch("app.core.dependencies.get_db", return_value=mock_db),
        patch("app.integrations.aws.get_s3_client", return_value=mock_s3),
        patch("app.integrations.supabase_client.get_supabase_client", return_value=mock_db),
    ):
        from app.main import app

        yield TestClient(app)
