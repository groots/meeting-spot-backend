import unittest
from unittest.mock import MagicMock, patch

from app.utils.geocoding import reverse_geocode_coordinates


class TestReverseGeocoding(unittest.TestCase):
    """Test cases for the reverse_geocode_coordinates function."""

    @patch("app.utils.geocoding.requests.get")
    @patch("app.utils.geocoding.current_app")
    def test_reverse_geocode_coordinates_success(self, mock_app, mock_get):
        """Test successful reverse geocoding with a mock response."""
        # Set up mock API key
        mock_app.config.get.return_value = "fake_api_key"

        # Set up mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "formatted_address": "123 Main St, San Francisco, CA 94105, USA",
                    "address_components": [
                        {"types": ["street_number"]},
                        {"types": ["route"]},
                        {"types": ["locality"]},
                    ],
                    "types": ["street_address"],
                }
            ],
        }
        mock_get.return_value = mock_response

        # Call the function with test coordinates
        lat, lng = 37.7749, -122.4194
        result = reverse_geocode_coordinates(lat, lng)

        # Check function called the API with expected parameters
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["latlng"], f"{lat},{lng}")
        self.assertEqual(kwargs["params"]["key"], "fake_api_key")

        # Validate the returned result
        self.assertTrue(result["success"])
        self.assertEqual(result["formatted_address"], "123 Main St, San Francisco, CA 94105, USA")
        self.assertEqual(result["quality"], "high")

    @patch("app.utils.geocoding.current_app")
    def test_reverse_geocode_coordinates_no_api_key(self, mock_app):
        """Test behavior when no API key is provided."""
        # Set up mock to return None for API key
        mock_app.config.get.return_value = None

        # Call the function
        result = reverse_geocode_coordinates(37.7749, -122.4194)

        # Validate error handling
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Geocoding service not configured")

    @patch("app.utils.geocoding.requests.get")
    @patch("app.utils.geocoding.current_app")
    def test_reverse_geocode_coordinates_no_results(self, mock_app, mock_get):
        """Test behavior when the API returns no results."""
        # Set up mock API key
        mock_app.config.get.return_value = "fake_api_key"

        # Set up mock response with no results
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "OK", "results": []}
        mock_get.return_value = mock_response

        # Call the function
        result = reverse_geocode_coordinates(37.7749, -122.4194)

        # Validate error handling
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "No address found for the provided coordinates")

    @patch("app.utils.geocoding.requests.get")
    @patch("app.utils.geocoding.current_app")
    def test_reverse_geocode_coordinates_api_error(self, mock_app, mock_get):
        """Test behavior when the API returns an error status."""
        # Set up mock API key
        mock_app.config.get.return_value = "fake_api_key"

        # Set up mock response with error status
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "ZERO_RESULTS",
            "error_message": "The provided location is invalid",
        }
        mock_get.return_value = mock_response

        # Call the function
        result = reverse_geocode_coordinates(37.7749, -122.4194)

        # Validate error handling
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Reverse geocoding failed: ZERO_RESULTS")

    @patch("app.utils.geocoding.requests.get")
    @patch("app.utils.geocoding.current_app")
    def test_reverse_geocode_coordinates_request_exception(self, mock_app, mock_get):
        """Test behavior when a request exception occurs."""
        # Set up mock API key
        mock_app.config.get.return_value = "fake_api_key"

        # Set up mock to raise an exception
        mock_get.side_effect = Exception("Network error")

        # Call the function
        result = reverse_geocode_coordinates(37.7749, -122.4194)

        # Validate error handling
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Reverse geocoding service error: Network error")

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
