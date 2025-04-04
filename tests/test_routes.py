"""Test the API routes."""

import json

from app.models import MeetingRequestStatus


def test_create_request(client) -> None:
    """Test creating a new meeting request."""
    data = {
        "address_a": "123 Test St, San Francisco, CA 94105",
        "location_type": "cafe",
        "user_b_contact_type": "email",
        "user_b_contact": "test@example.com",
    }

    response = client.post(
        "/api/v2/meeting-requests/",
        data=json.dumps(data),
        content_type="application/json",
    )

    print(f"Response status: {response.status_code}")
    print(f"Response data: {response.data}")

    assert response.status_code == 201


def test_get_request_status(client, test_meeting_request) -> None:
    """Test getting the status of a meeting request."""
    response = client.get(f"/api/v2/meeting-requests/{test_meeting_request.request_id}/status")

    assert response.status_code == 200
    result = json.loads(response.data)
    assert "status" in result
    assert result["status"] == MeetingRequestStatus.PENDING_B_ADDRESS.value


def test_respond_to_request(client, test_meeting_request) -> None:
    """Test responding to a meeting request."""
    # First, get the token from the request creation
    response = client.get(f"/api/v2/meeting-requests/{test_meeting_request.request_id}/status")
    assert response.status_code == 200
    result = json.loads(response.data)
    assert "status" in result

    # Now submit the response with address B
    data = {
        "address_b": "456 Test Ave, Test City, TS 12345",
        "token": test_meeting_request.token_b,
    }
    response = client.post(
        f"/api/v2/meeting-requests/{test_meeting_request.request_id}/respond",
        data=json.dumps(data),
        content_type="application/json",
    )
    assert response.status_code == 200


def test_get_request_results(client, test_meeting_request) -> None:
    """Test getting the results of a meeting request."""
    response = client.get(f"/api/v2/meeting-requests/{test_meeting_request.request_id}/results")

    assert response.status_code == 200
    result = json.loads(response.data)
    assert "status" in result
