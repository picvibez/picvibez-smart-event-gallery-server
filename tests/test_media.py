from unittest.mock import MagicMock, patch


def test_presign_unauthenticated(client):
    response = client.post("/api/v1/events/event-123/media/presign", json={
        "file_name": "photo.jpg",
        "file_size_bytes": 1000000,
        "media_type": "image",
    })
    assert response.status_code == 401


def test_presign_authenticated(client, auth_token, mock_db):
    """Ensure authenticated users can reach the presign endpoint."""
    response = client.post(
        "/api/v1/events/11111111-1111-1111-1111-111111111111/media/presign",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={
            "file_name": "photo.jpg",
            "file_size_bytes": 1000000,
            "media_type": "image",
        },
    )
    # Should not be 401 -- auth works
    assert response.status_code != 401
