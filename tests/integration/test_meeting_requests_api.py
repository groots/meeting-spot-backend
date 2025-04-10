import uuid

import pytest
from flask import url_for
from flask_jwt_extended import get_jwt_identity

from app import db
from app.models import ContactType, MeetingRequest, MeetingRequestStatus, User


def test_create_meeting_request(client, auth_headers):
    """Test creating a new meeting request."""
    data = {
        "address_a": "123 Test St, San Francisco, CA 94105",  # API expects address string
        "location_type": "cafe",
        "user_b_contact_type": ContactType.EMAIL.value,
        "user_b_contact": "contact@example.com",
    }
    response = client.post("/api/v1/meeting-requests/", json=data, headers=auth_headers)
    assert response.status_code == 201
    assert response.json["status"] == MeetingRequestStatus.PENDING_B_ADDRESS.value


def test_get_meeting_request(client, test_meeting_request, auth_headers):
    """Test getting a specific meeting request."""
    response = client.get(
        f"/api/v1/meeting-requests/{test_meeting_request.request_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json["request_id"] == str(test_meeting_request.request_id)


def test_get_meeting_request_not_found(client, auth_headers):
    """Test getting a non-existent meeting request."""
    response = client.get(
        f"/api/v1/meeting-requests/{uuid.uuid4()}",
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_get_meeting_requests_list(client, test_meeting_request, auth_headers):
    """Test getting list of meeting requests."""
    response = client.get("/api/v1/meeting-requests/", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json, list)
    assert len(response.json) > 0


def test_update_meeting_request(client, test_meeting_request, auth_headers):
    """Test updating a meeting request."""
    data = {
        "address_b_lat": 37.7833,
        "address_b_lon": -122.4167,
    }
    response = client.put(
        f"/api/v1/meeting-requests/{test_meeting_request.request_id}",
        json=data,
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json["status"] == MeetingRequestStatus.CALCULATING.value


def test_delete_meeting_request(client, test_meeting_request, auth_headers):
    """Test deleting a meeting request."""
    response = client.delete(
        f"/api/v1/meeting-requests/{test_meeting_request.request_id}",
        headers=auth_headers,
    )
    assert response.status_code == 204
