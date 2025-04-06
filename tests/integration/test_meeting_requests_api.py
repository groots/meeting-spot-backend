import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from flask import url_for

from app.models import ContactType, MeetingRequest, MeetingRequestStatus


@pytest.fixture
def app_client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture
def mock_meeting_request(db_session):
    """Create a mock meeting request for testing."""
    request = MeetingRequest(
        address_a_lat=37.7749,
        address_a_lon=-122.4194,
        location_type="Restaurant / Food",
        user_b_contact_type=ContactType.EMAIL,
        user_b_contact="test@example.com",
        token_b=uuid.uuid4().hex,
        status=MeetingRequestStatus.PENDING_B_ADDRESS,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    db_session.add(request)
    db_session.commit()
    return request


def test_create_meeting_request(app_client):
    """Test creating a new meeting request."""
    data = {
        "address_a": "123 Main St, San Francisco, CA",
        "location_type": "Restaurant / Food",
        "user_b_contact_type": "email",
        "user_b_contact": "test@example.com",
    }

    response = app_client.post(
        "/api/v1/meeting-requests/",
        data=json.dumps(data),
        content_type="application/json",
    )

    assert response.status_code == 201
    response_data = json.loads(response.data)

    assert "request_id" in response_data
    assert response_data["location_type"] == data["location_type"]
    assert response_data["user_b_contact_type"] == data["user_b_contact_type"]
    assert response_data["status"] == MeetingRequestStatus.PENDING_B_ADDRESS.value
    assert "token_b" in response_data


def test_get_meeting_request(app_client, mock_meeting_request):
    """Test getting a meeting request by ID."""
    response = app_client.get(f"/api/v1/meeting-requests/{mock_meeting_request.request_id}")

    assert response.status_code == 200
    response_data = json.loads(response.data)

    assert response_data["id"] == str(mock_meeting_request.request_id)
    assert response_data["location_type"] == mock_meeting_request.location_type
    assert response_data["user_b_contact_type"] == mock_meeting_request.user_b_contact_type.value
    assert response_data["status"] == mock_meeting_request.status.value


def test_get_meeting_request_status(app_client, mock_meeting_request):
    """Test getting the status of a meeting request."""
    response = app_client.get(f"/api/v1/meeting-requests/{mock_meeting_request.request_id}/status/")

    assert response.status_code == 200
    response_data = json.loads(response.data)

    assert response_data["request_id"] == str(mock_meeting_request.request_id)
    assert response_data["status"] == mock_meeting_request.status.value
    assert "created_at" in response_data
    assert "expires_at" in response_data


def test_respond_to_meeting_request(app_client, mock_meeting_request):
    """Test responding to a meeting request."""
    data = {
        "address_b": "456 Market St, San Francisco, CA",
        "token": mock_meeting_request.token_b,
    }

    response = app_client.post(
        f"/api/v1/meeting-requests/{mock_meeting_request.request_id}/respond/",
        data=json.dumps(data),
        content_type="application/json",
    )

    assert response.status_code == 200
    response_data = json.loads(response.data)

    assert response_data["status"] == MeetingRequestStatus.CALCULATING.value

    # Verify the request was updated in the database
    updated_request = MeetingRequest.query.get(mock_meeting_request.request_id)
    assert updated_request.status == MeetingRequestStatus.CALCULATING
    assert updated_request.address_b_lat is not None
    assert updated_request.address_b_lon is not None


def test_get_meeting_request_results(app_client, mock_meeting_request):
    """Test getting the results of a meeting request."""
    # First, update the request to completed status with some mock results
    mock_meeting_request.status = MeetingRequestStatus.COMPLETED
    mock_meeting_request.suggested_options = [
        {
            "name": "Test Restaurant",
            "address": "123 Test St",
            "distance": 1.5,
            "rating": 4.5,
        }
    ]
    mock_meeting_request.selected_place_details = {
        "name": "Selected Restaurant",
        "address": "456 Selected St",
        "distance": 2.0,
        "rating": 4.8,
    }

    response = app_client.get(f"/api/v1/meeting-requests/{mock_meeting_request.request_id}/results/")

    assert response.status_code == 200
    response_data = json.loads(response.data)

    assert response_data["request_id"] == str(mock_meeting_request.request_id)
    assert response_data["status"] == MeetingRequestStatus.COMPLETED.value
    assert "suggested_options" in response_data
    assert "selected_place" in response_data
