import unittest
from unittest.mock import MagicMock, patch

from app.utils.geocoding import reverse_geocode_coordinates


class TestReverseGeocoding(unittest.TestCase):
    """Unit tests for reverse geocoding functionality."""

    @patch("app.utils.geocoding.requests.get")
    def test_reverse_geocode_coordinates_success(self, mock_get):
        """Test successful reverse geocoding."""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "formatted_address": "123 Test St, San Francisco, CA 94105, USA",
                    "types": ["street_address"],
                }
            ],
        }
        mock_get.return_value = mock_response

        # Call the function with test API key
        api_key = "fake_api_key"
        result = reverse_geocode_coordinates(37.7749, -122.4194, api_key)

        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(result["formatted_address"], "123 Test St, San Francisco, CA 94105, USA")
        self.assertEqual(result["quality"], "high")

        # Verify that the API was called with correct parameters
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["latlng"], "37.7749,-122.4194")
        self.assertEqual(kwargs["params"]["key"], api_key)

    @patch("app.utils.geocoding.requests.get")
    def test_reverse_geocode_coordinates_no_results(self, mock_get):
        """Test reverse geocoding with no results."""
        # Mock API response with no results
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ZERO_RESULTS", "results": []}
        mock_get.return_value = mock_response

        # Call the function
        result = reverse_geocode_coordinates(0, 0, "fake_api_key")  # Ocean location, no address

        # Verify the result indicates failure
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "No results found for the given coordinates")

    @patch("app.utils.geocoding.current_app")
    def test_reverse_geocode_coordinates_no_api_key(self, mock_current_app):
        """Test reverse geocoding with no API key."""
        # Mock app config with no API key
        mock_current_app.config.get.return_value = None

        # Call the function without providing an API key
        result = reverse_geocode_coordinates(37.7749, -122.4194)

        # Verify the result indicates failure due to missing API key
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Geocoding service not configured")

    @patch("app.utils.geocoding.requests.get")
    def test_reverse_geocode_coordinates_api_error(self, mock_get):
        """Test reverse geocoding with API error."""
        # Mock API response with error
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "REQUEST_DENIED",
            "error_message": "The provided API key is invalid.",
        }
        mock_get.return_value = mock_response

        # Call the function
        result = reverse_geocode_coordinates(37.7749, -122.4194, "invalid_key")

        # Verify the result indicates failure due to API error
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "The provided API key is invalid.")

    def test_reverse_geocode_coordinates_invalid_coordinates(self):
        """Test reverse geocoding with invalid coordinates."""
        # Test with latitude > 90
        result = reverse_geocode_coordinates(91, -122.4194, "fake_api_key")
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Invalid latitude/longitude values")

        # Test with longitude < -180
        result = reverse_geocode_coordinates(37.7749, -190, "fake_api_key")
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Invalid latitude/longitude values")

    @patch("app.utils.geocoding.requests.get")
    @patch("app.utils.geocoding.current_app")
    def test_reverse_geocode_coordinates_medium_quality(self, mock_app, mock_get):
        """Test response with medium quality address (no street number)."""
        # Set up mock API key
        mock_app.config.get.return_value = "fake_api_key"

        # Set up mock response with medium quality address (missing street number)
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "formatted_address": "Main St, San Francisco, CA 94105, USA",
                    "address_components": [
                        {"types": ["route"]},
                        {"types": ["locality"]},
                    ],
                    "types": ["route"],
                }
            ],
        }
        mock_get.return_value = mock_response

        # Call the function
        result = reverse_geocode_coordinates(37.7749, -122.4194)

        # Validate the quality assessment
        self.assertTrue(result["success"])
        self.assertEqual(result["quality"], "medium")

    @patch("app.utils.geocoding.requests.get")
    @patch("app.utils.geocoding.current_app")
    def test_reverse_geocode_coordinates_low_quality(self, mock_app, mock_get):
        """Test response with low quality address (only administrative area)."""
        # Set up mock API key
        mock_app.config.get.return_value = "fake_api_key"

        # Set up mock response with low quality address (missing route and street number)
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "formatted_address": "San Francisco, CA, USA",
                    "address_components": [
                        {"types": ["administrative_area_level_2"]},
                    ],
                    "types": ["administrative_area_level_2"],
                }
            ],
        }
        mock_get.return_value = mock_response

        # Call the function
        result = reverse_geocode_coordinates(37.7749, -122.4194)

        # Validate the quality assessment
        self.assertTrue(result["success"])
        self.assertEqual(result["quality"], "low")
