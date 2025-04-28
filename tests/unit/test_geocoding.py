from unittest.mock import MagicMock, patch

import pytest

from app.utils.geocoding import geocode_address


@pytest.fixture
def mock_current_app():
    """Mock the current_app"""
    with patch("app.utils.geocoding.current_app") as mock_app:
        mock_app.config = {"GOOGLE_MAPS_API_KEY": "test_api_key"}
        yield mock_app


@pytest.fixture
def mock_requests():
    """Mock the requests module"""
    with patch("app.utils.geocoding.requests") as mock_req:
        yield mock_req


def test_geocode_address_success(mock_current_app, mock_requests):
    """Test successful geocoding"""
    # Mock successful response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "OK",
        "results": [
            {
                "formatted_address": "123 Test Street, City, Country",
                "geometry": {"location": {"lat": 37.7749, "lng": -122.4194}},
            }
        ],
    }
    mock_requests.get.return_value = mock_response

    # Call the function
    result = geocode_address("123 Test Street")

    # Check the result
    assert result["success"] is True
    assert result["coordinates"]["lat"] == 37.7749
    assert result["coordinates"]["lng"] == -122.4194
    assert result["formatted_address"] == "123 Test Street, City, Country"

    # Verify the request was made correctly
    mock_requests.get.assert_called_once()
    args, kwargs = mock_requests.get.call_args
    assert args[0] == "https://maps.googleapis.com/maps/api/geocode/json"
    assert kwargs["params"]["address"] == "123 Test Street"
    assert kwargs["params"]["key"] == "test_api_key"


def test_geocode_address_no_api_key(mock_current_app):
    """Test geocoding with no API key"""
    # Set no API key
    mock_current_app.config = {}

    # Call the function
    result = geocode_address("123 Test Street")

    # Check the result
    assert result["success"] is False
    assert "error" in result
    assert "not configured" in result["error"]


def test_geocode_address_empty_input():
    """Test geocoding with empty input"""
    # Call the function with empty address
    result = geocode_address("")

    # Check the result
    assert result["success"] is False
    assert "error" in result
    assert "No address provided" in result["error"]


def test_geocode_address_api_error(mock_current_app, mock_requests):
    """Test geocoding when API returns an error"""
    # Mock error response
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "ZERO_RESULTS", "results": []}
    mock_requests.get.return_value = mock_response

    # Call the function
    result = geocode_address("non-existent address")

    # Check the result
    assert result["success"] is False
    assert "error" in result
    assert "ZERO_RESULTS" in result["error"]


def test_geocode_address_request_exception(mock_current_app, mock_requests):
    """Test geocoding when a request exception occurs"""
    # Mock request exception
    mock_requests.get.side_effect = Exception("Network error")

    # Call the function
    result = geocode_address("123 Test Street")

    # Check the result
    assert result["success"] is False
    assert "error" in result
    assert "Network error" in result["error"]
