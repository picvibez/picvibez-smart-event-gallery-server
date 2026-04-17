from unittest.mock import MagicMock

TEST_UUID = "11111111-1111-1111-1111-111111111111"


def test_create_event_unauthenticated(client):
    response = client.post("/api/v1/events", json={"name": "My Wedding"})
    assert response.status_code == 401


def test_list_events_unauthenticated(client):
    response = client.get("/api/v1/events")
    assert response.status_code == 401


def test_create_event_authenticated(client, auth_token, mock_db):
    """Ensure authenticated users can hit the create event endpoint."""
    mock_event = {
        "id": TEST_UUID,
        "name": "My Wedding",
        "event_type": "Wedding",
        "start_time": None,
        "end_time": None,
        "privacy_mode": "public",
        "storage_limit_bytes": 536870912,
        "current_storage_bytes": 0,
        "is_watermark_enabled": True,
        "created_by": "test-user-id-123",
        "created_at": "2025-01-01T00:00:00+00:00",
    }

    insert_result = MagicMock()
    insert_result.data = [mock_event]
    mock_db.table.return_value.insert.return_value.execute.return_value = insert_result

    response = client.post(
        "/api/v1/events",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"name": "My Wedding"},
    )
    # Auth passes -- endpoint is reachable (not 401/405)
    assert response.status_code != 401
    assert response.status_code != 405
