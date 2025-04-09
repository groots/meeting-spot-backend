import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models import ContactType, MeetingRequest, MeetingRequestStatus


def test_create_request(client, auth_headers) -> None:
    """Test creating a new meeting request."""
    data = {
        "address_a_lat": 37.7749,
        "address_a_lon": -122.4194,
        "location_type": "cafe",
        "user_b_contact_type": "email",
        "user_b_contact": "test@example.com",
    }

    response = client.post(
        "/api/v1/meeting-requests/",
        data=json.dumps(data),
        content_type="application/json",
        headers=auth_headers,
    )

    print(f"Response status: {response.status_code}")
    print(f"Response data: {response.data}")

    assert response.status_code == 201


def test_get_request_status(client, test_meeting_request, auth_headers) -> None:
    """Test getting the status of a meeting request."""
    response = client.get(
        f"/api/v1/meeting-requests/{test_meeting_request.request_id}/status",
        headers=auth_headers,
    )

    assert response.status_code == 200
    result = json.loads(response.data)
    assert "status" in result
    assert result["status"] == MeetingRequestStatus.PENDING_B_ADDRESS.value


def test_respond_to_request(client, test_meeting_request, auth_headers) -> None:
    """Test responding to a meeting request."""
    # First, get the token from the request creation
    response = client.get(
        f"/api/v1/meeting-requests/{test_meeting_request.request_id}/status",
        headers=auth_headers,
    )
    assert response.status_code == 200
    result = json.loads(response.data)
    assert "status" in result

    # Now submit the response with address B
    data = {
        "address_b": "456 Test Ave, Test City, TS 12345",
        "token": test_meeting_request.token_b,
    }
    response = client.post(
        f"/api/v1/meeting-requests/{test_meeting_request.request_id}/respond/",
        data=json.dumps(data),
        content_type="application/json",
        headers=auth_headers,
    )
    assert response.status_code == 200


def test_get_request_results(client, test_meeting_request, auth_headers) -> None:
    """Test getting the results of a meeting request."""
    response = client.get(
        f"/api/v1/meeting-requests/{test_meeting_request.request_id}/results/",
        headers=auth_headers,
    )

    assert response.status_code == 200
    result = json.loads(response.data)
    assert "status" in result
