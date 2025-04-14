import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from flask import url_for

from app import db
from app.models import MeetingRequest, User
from app.models.enums import ContactType, MeetingRequestStatus


@pytest.fixture
def auth_user(client):
    """Create a test user and return auth headers"""
    from app.models.user import User

    # Create a test user
    user = User(email="test_integration@example.com")
    user.set_password("TestPassword123!")

    # Save to database
    db.session.add(user)
    db.session.commit()

    # Log in and get token
    response = client.post(
        "/api/v1/auth/login", json={"email": "test_integration@example.com", "password": "TestPassword123!"}
    )

    token = response.json.get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    yield user, headers

    # Clean up
    db.session.delete(user)
    db.session.commit()


@pytest.fixture
def mock_location_api():
    """Mock the location API calls"""
    with patch("app.utils.location.find_meeting_spots") as mock_find:
        # Set up mock return value for find_meeting_spots
        mock_spots = [
            {
                "name": "Test Restaurant",
                "place_id": "place123",
                "address": "123 Test St",
                "location": {"lat": 37.78, "lng": -122.41},
                "rating": 4.5,
                "price_level": 2,
                "photos": ["https://example.com/photo.jpg"],
                "distance": 1.2,
                "types": ["restaurant", "food"],
                "category": "Food & Drink",
                "subcategory": "fine dining",
            }
        ]
        mock_find.return_value = mock_spots
        yield mock_find


def test_meeting_request_full_flow(client, auth_user, mock_location_api):
    """Test the complete meeting request flow from creation to completion."""
    user, auth_headers = auth_user

    # Step 1: Create a meeting request
    create_data = {
        "address_a": "123 Test St, San Francisco, CA",
        "location_type": "Food & Drink: fine dining",
        "user_b_contact_type": "EMAIL",
        "user_b_contact": "friend@example.com",
    }

    response = client.post("/api/v1/meeting-requests/", json=create_data, headers=auth_headers)

    assert response.status_code == 201
    request_id = response.json["request_id"]
    token_b = response.json["token_b"]
    assert response.json["status"] == MeetingRequestStatus.PENDING_B_ADDRESS.value

    # Step 2: Fetch the meeting request to confirm it was created
    response = client.get(f"/api/v1/meeting-requests/{request_id}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json["request_id"] == request_id
    assert response.json["status"] == MeetingRequestStatus.PENDING_B_ADDRESS.value
    assert response.json["location_type"] == "Food & Drink: fine dining"

    # Step 3: Respond to the meeting request (User B submits address)
    respond_data = {
        "address_b": "456 Test Ave, New York, NY",
        "token": token_b,
        "address_b_lat": 40.7128,
        "address_b_lon": -74.0060,
    }

    response = client.post(f"/api/v1/meeting-requests/{request_id}/respond", json=respond_data)

    assert response.status_code == 200
    assert response.json["status"] == MeetingRequestStatus.COMPLETED.value

    # Verify that find_meeting_spots was called with expected parameters
    mock_location_api.assert_called()

    # Step 4: Get the results
    response = client.get(f"/api/v1/meeting-requests/{request_id}/results", headers=auth_headers)

    assert response.status_code == 200
    assert response.json["status"] == MeetingRequestStatus.COMPLETED.value
    assert len(response.json["suggested_options"]) > 0
    assert response.json["suggested_options"][0]["name"] == "Test Restaurant"
    assert "midpoint" in response.json

    # Clean up
    client.delete(f"/api/v1/meeting-requests/{request_id}", headers=auth_headers)


def test_meeting_request_invalid_token(client, auth_user):
    """Test responding to a meeting request with an invalid token."""
    user, auth_headers = auth_user

    # Create a meeting request
    create_data = {
        "address_a": "123 Test St, San Francisco, CA",
        "location_type": "Food & Drink",
        "user_b_contact_type": "EMAIL",
        "user_b_contact": "friend@example.com",
    }

    response = client.post("/api/v1/meeting-requests/", json=create_data, headers=auth_headers)

    assert response.status_code == 201
    request_id = response.json["request_id"]

    # Try to respond with invalid token
    respond_data = {
        "address_b": "456 Test Ave, New York, NY",
        "token": "invalid_token",
        "address_b_lat": 40.7128,
        "address_b_lon": -74.0060,
    }

    response = client.post(f"/api/v1/meeting-requests/{request_id}/respond", json=respond_data)

    assert response.status_code == 400
    assert "Invalid token" in response.json.get("error", "")

    # Clean up
    client.delete(f"/api/v1/meeting-requests/{request_id}", headers=auth_headers)


def test_different_categories(client, auth_user, mock_location_api):
    """Test creating meeting requests with different categories and subcategories."""
    user, auth_headers = auth_user

    # Test categories with subcategories
    categories = [
        "Food & Drink: fine dining",
        "Food & Drink: cheap eats",
        "Food & Drink: hole in the wall",
        "Night Life",
        "Cultural",
        "Shopping",
    ]

    for category in categories:
        create_data = {
            "address_a": "123 Test St, San Francisco, CA",
            "location_type": category,
            "user_b_contact_type": "EMAIL",
            "user_b_contact": "friend@example.com",
        }

        response = client.post("/api/v1/meeting-requests/", json=create_data, headers=auth_headers)

        assert response.status_code == 201
        request_id = response.json["request_id"]
        token_b = response.json["token_b"]

        # Verify location_type was saved correctly
        response = client.get(f"/api/v1/meeting-requests/{request_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json["location_type"] == category

        # Clean up
        client.delete(f"/api/v1/meeting-requests/{request_id}", headers=auth_headers)
