import unittest
from unittest.mock import MagicMock, patch

import pytest

from app.utils.geocoding import geocode_address, reverse_geocode_coordinates


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
                "address_components": [
                    {"types": ["street_number"]},
                    {"types": ["route"]},
                    {"types": ["locality"]},
                ],
            }
        ],
    }
    mock_requests.get.return_value = mock_response

    # Call the function
    result = geocode_address("123 Test Street, City, Country")

    # Check the result
    assert result["success"] is True
    assert result["coordinates"]["lat"] == 37.7749
    assert result["coordinates"]["lng"] == -122.4194
    assert result["formatted_address"] == "123 Test Street, City, Country"

    # Verify the request was made correctly
    mock_requests.get.assert_called_once()
    args, kwargs = mock_requests.get.call_args
    assert args[0] == "https://maps.googleapis.com/maps/api/geocode/json"
    assert kwargs["params"]["address"] == "123 Test Street, City, Country"
    assert kwargs["params"]["key"] == "test_api_key"


def test_geocode_address_no_api_key(mock_current_app):
    """Test geocoding with no API key"""
    # Set no API key
    mock_current_app.config = {}

    # Call the function
    result = geocode_address("123 Test Street, City, Country")

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

    # Call the function with a complete address to pass validation
    result = geocode_address("123 Test Street, City, 12345")

    # Check the result
    assert result["success"] is False
    assert "error" in result
    assert "ZERO_RESULTS" in result["error"]


def test_geocode_address_request_exception(mock_current_app, mock_requests):
    """Test geocoding when a request exception occurs"""
    # Mock request exception
    mock_requests.get.side_effect = Exception("Network error")

    # Call the function with a complete address to pass validation
    result = geocode_address("123 Test Street, City, 12345")

    # Check the result
    assert result["success"] is False
    assert "error" in result
    assert "Network error" in result["error"]


class TestGeocoding(unittest.TestCase):
    """Unit tests for geocoding utility functions."""

    @patch("app.utils.geocoding.requests.get")
    def test_geocode_address_success(self, mock_get):
        """Test geocoding an address successfully."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "formatted_address": "123 Main St, San Francisco, CA 94105, USA",
                    "geometry": {"location": {"lat": 37.7749, "lng": -122.4194}},
                }
            ],
        }
        mock_get.return_value = mock_response

        # Call the geocode function
        result = geocode_address("123 Main St, San Francisco, CA", "test_api_key")

        # Check the result
        self.assertTrue(result["success"])
        self.assertEqual(result["formatted_address"], "123 Main St, San Francisco, CA 94105, USA")
        self.assertEqual(result["lat"], 37.7749)
        self.assertEqual(result["lng"], -122.4194)

        # Verify the API was called correctly
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["address"], "123 Main St, San Francisco, CA")
        self.assertEqual(kwargs["params"]["key"], "test_api_key")

    @patch("app.utils.geocoding.requests.get")
    def test_geocode_address_no_results(self, mock_get):
        """Test geocoding with no results returned."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ZERO_RESULTS", "results": []}
        mock_get.return_value = mock_response

        # Call the geocode function
        result = geocode_address("Invalid Address XYZ", "test_api_key")

        # Check the result
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "No results found for the given address")

    @patch("app.utils.geocoding.requests.get")
    def test_geocode_address_api_error(self, mock_get):
        """Test geocoding with API error."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "REQUEST_DENIED", "error_message": "API key is invalid"}
        mock_get.return_value = mock_response

        # Call the geocode function
        result = geocode_address("123 Main St", "invalid_key")

        # Check the result
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "API key is invalid")

    @patch("app.utils.geocoding.requests.get")
    def test_geocode_address_exception(self, mock_get):
        """Test geocoding with exception during request."""
        # Mock the API to raise an exception
        mock_get.side_effect = Exception("Connection error")

        # Call the geocode function
        result = geocode_address("123 Main St", "test_api_key")

        # Check the result
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Error during geocoding: Connection error")

    @patch("app.utils.geocoding.requests.get")
    def test_reverse_geocode_success(self, mock_get):
        """Test reverse geocoding successfully."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "formatted_address": "123 Main St, San Francisco, CA 94105, USA",
                    "types": ["street_address"],
                    "address_components": [
                        {"types": ["street_number"], "long_name": "123"},
                        {"types": ["route"], "long_name": "Main St"},
                        {"types": ["locality"], "long_name": "San Francisco"},
                    ],
                }
            ],
        }
        mock_get.return_value = mock_response

        # Call the reverse geocode function
        result = reverse_geocode_coordinates(37.7749, -122.4194, "test_api_key")

        # Check the result
        self.assertTrue(result["success"])
        self.assertEqual(result["formatted_address"], "123 Main St, San Francisco, CA 94105, USA")
        self.assertEqual(result["quality"], "high")  # It's a street_address, so quality is high

        # Verify the API was called correctly
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["latlng"], "37.7749,-122.4194")
        self.assertEqual(kwargs["params"]["key"], "test_api_key")

    @patch("app.utils.geocoding.requests.get")
    def test_reverse_geocode_approximate_result(self, mock_get):
        """Test reverse geocoding with an approximate result."""
        # Mock the API response with a less precise result
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "formatted_address": "San Francisco, CA 94105, USA",
                    "types": ["locality", "political"],  # Not a street address
                    "address_components": [
                        {"types": ["locality"], "long_name": "San Francisco"},
                        {"types": ["administrative_area_level_1"], "long_name": "California"},
                    ],
                }
            ],
        }
        mock_get.return_value = mock_response

        # Call the reverse geocode function
        result = reverse_geocode_coordinates(37.7749, -122.4194, "test_api_key")

        # Check the result
        self.assertTrue(result["success"])
        self.assertEqual(result["formatted_address"], "San Francisco, CA 94105, USA")
        self.assertEqual(result["quality"], "medium")  # It's a locality, not a street address

    @patch("app.utils.geocoding.requests.get")
    def test_reverse_geocode_no_results(self, mock_get):
        """Test reverse geocoding with no results."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ZERO_RESULTS", "results": []}
        mock_get.return_value = mock_response

        # Call the reverse geocode function
        result = reverse_geocode_coordinates(0, 0, "test_api_key")  # Invalid coordinates in ocean

        # Check the result
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "No results found for the given coordinates")

    @patch("app.utils.geocoding.requests.get")
    def test_reverse_geocode_api_error(self, mock_get):
        """Test reverse geocoding with API error."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "OVER_QUERY_LIMIT",
            "error_message": "You have exceeded your daily request quota",
        }
        mock_get.return_value = mock_response

        # Call the reverse geocode function
        result = reverse_geocode_coordinates(37.7749, -122.4194, "test_api_key")

        # Check the result
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "You have exceeded your daily request quota")

    def test_invalid_parameters(self):
        """Test geocoding with invalid parameters."""
        # Test with empty address
        result = geocode_address("", "test_api_key")
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Address cannot be empty")

        # Test with empty API key
        result = geocode_address("123 Main St", "")
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "API key cannot be empty")

        # Test reverse geocoding with invalid coordinates
        result = reverse_geocode_coordinates(91, -122.4194, "test_api_key")  # Latitude > 90
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Invalid latitude/longitude values")

        result = reverse_geocode_coordinates(37.7749, -190, "test_api_key")  # Longitude < -180
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Invalid latitude/longitude values")
