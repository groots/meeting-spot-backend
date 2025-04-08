import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from flask import url_for

from app.models import Contact, ContactType, MeetingRequest, MeetingRequestStatus, User


@pytest.fixture
def app_client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture
def mock_user(_session):
    """Create a mock user for testing."""
    user = User(
        email="test@example.com",
    )
    user.set_password("testpassword")
    _session.add(user)
    _session.commit()
    return user


@pytest.fixture
def mock_contact(mock_user, _session):
    """Create a mock contact for testing."""
    contact = Contact(
        user_id=mock_user.id,
        contact_email="contact@example.com",
        nickname="Test Contact",
    )
    _session.add(contact)
    _session.commit()
    return contact


@pytest.fixture
def mock_meeting_request(_session):
    """Create a mock meeting request for testing."""
    request = MeetingRequest(
        request_id=uuid.uuid4(),
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
    _session.add(request)
    _session.flush()  # Ensure the object is persisted without committing transaction

    # Verify the request exists in the database
    queried_request = MeetingRequest.query.get(request.request_id)
    assert queried_request is not None, "Meeting request was not persisted to database"

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
    assert "id" in response_data
    assert response_data["location_type"] == data["location_type"]
    assert "user_b_contact_encrypted" in response_data
    assert response_data["user_b_contact_type"] == data["user_b_contact_type"]


def test_create_meeting_request_with_contact(app_client, mock_user, mock_contact):
    """Test creating a new meeting request using a contact from the address book."""
    data = {
        "address_a": "123 Main St, San Francisco, CA",
        "location_type": "Restaurant / Food",
        "user_b_contact_type": "email",
        "user_b_contact": mock_contact.contact_email,
    }

    # Login as the user
    auth_response = app_client.post(
        "/api/v1/auth/login",
        data=json.dumps({"email": "test@example.com", "password": "testpassword"}),
        content_type="application/json",
    )
    assert auth_response.status_code == 200
    token = json.loads(auth_response.data)["access_token"]

    # Create meeting request with contact
    response = app_client.post(
        "/api/v1/meeting-requests/",
        data=json.dumps(data),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    response_data = json.loads(response.data)
    assert "request_id" in response_data
    assert response_data["location_type"] == data["location_type"]
    assert response_data["user_b_contact_type"] == data["user_b_contact_type"]


def test_get_meeting_request(app_client, mock_meeting_request, _session):
    """Test retrieving a meeting request by ID."""
    # Debug: Verify the meeting request exists in the database
    queried_request = MeetingRequest.query.get(mock_meeting_request.request_id)
    print(f"\nMeeting request in database: {queried_request}")
    print(f"Meeting request ID: {mock_meeting_request.request_id}")
    print(f"All meeting requests: {[str(r.request_id) for r in MeetingRequest.query.all()]}")

    # Make the request
    response = app_client.get(f"/api/v1/meeting-requests/{mock_meeting_request.request_id}")
    print(f"Response status: {response.status_code}")
    print(f"Response data: {response.data.decode()}")

    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data["id"] == str(mock_meeting_request.request_id)


def test_get_meeting_request_with_contact(app_client, mock_user, mock_contact, _session):
    """Test retrieving a meeting request that uses a contact from the address book."""
    # Create a meeting request with a contact
    request = MeetingRequest(
        request_id=uuid.uuid4(),
        address_a_lat=37.7749,
        address_a_lon=-122.4194,
        location_type="Restaurant / Food",
        user_b_contact_type=ContactType.EMAIL,
        user_b_contact=mock_contact.contact_email,
        token_b=uuid.uuid4().hex,
        status=MeetingRequestStatus.PENDING_B_ADDRESS,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    _session.add(request)
    _session.commit()

    response = app_client.get(f"/api/v1/meeting-requests/{request.request_id}")
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data["id"] == str(request.request_id)
    assert response_data["user_b_contact_type"] == ContactType.EMAIL.value


def test_get_meeting_request_status(app_client, mock_meeting_request, _session):
    """Test getting the status of a meeting request."""
    # Ensure the meeting request is committed
    _session.add(mock_meeting_request)
    _session.commit()

    response = app_client.get(f"/api/v1/meeting-requests/{mock_meeting_request.request_id}/status")
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data["request_id"] == str(mock_meeting_request.request_id)
    assert response_data["status"] == mock_meeting_request.status.value


def test_respond_to_meeting_request(app_client, mock_meeting_request):
    """Test responding to a meeting request."""
    data = {
        "address_b": "456 Market St, San Francisco, CA",
        "token": mock_meeting_request.token_b,
    }

    response = app_client.post(
        f"/api/v1/meeting-requests/{mock_meeting_request.request_id}/respond",
        data=json.dumps(data),
        content_type="application/json",
    )

    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data["status"] == MeetingRequestStatus.CALCULATING.value


def test_get_meeting_request_results(app_client, mock_meeting_request):
    """Test getting the results of a meeting request."""
    # Update meeting request with results
    mock_meeting_request.status = MeetingRequestStatus.COMPLETED
    mock_meeting_request.suggested_options = [{"name": "Test Place", "address": "123 Test St"}]
    mock_meeting_request.selected_place_google_id = "test_place_id"
    mock_meeting_request.selected_place_details = {
        "name": "Selected Place",
        "address": "456 Selected St",
    }

    response = app_client.get(f"/api/v1/meeting-requests/{mock_meeting_request.request_id}/results")
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data["status"] == MeetingRequestStatus.COMPLETED.value
    assert "suggested_options" in response_data
    assert "selected_place" in response_data
