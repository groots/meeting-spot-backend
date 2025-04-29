import unittest
from unittest.mock import MagicMock, patch

from app import create_app
from app.utils.geocoding import geocode_address, reverse_geocode_coordinates


class TestGeocodingIntegration(unittest.TestCase):
    """Integration tests for geocoding functions with app context."""

    def setUp(self):
        """Set up test app configuration."""
        self.app = create_app("testing")
        self.app.config["MAPS_API_KEY"] = "test_api_key"
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        """Clean up after tests."""
        self.app_context.pop()

    @patch("app.utils.geocoding.requests.get")
    def test_geocode_address_integration(self, mock_get):
        """Test geocode_address in app context."""
        # Mock the Google Maps API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "OK",
            "results": [
                {
                    "formatted_address": "123 Main St, San Francisco, CA 94105, USA",
                    "geometry": {"location": {"lat": 37.7749, "lng": -122.4194}},
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

        # Call the function
        result = geocode_address("123 Main St, San Francisco, CA")

        # Assert API was called with correct parameters
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["address"], "123 Main St, San Francisco, CA")
        self.assertEqual(kwargs["params"]["key"], "test_api_key")

        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(result["lat"], 37.7749)
        self.assertEqual(result["lng"], -122.4194)
        self.assertEqual(result["formatted_address"], "123 Main St, San Francisco, CA 94105, USA")
        self.assertEqual(result["quality"], "high")

    @patch("app.utils.geocoding.requests.get")
    def test_reverse_geocode_coordinates_integration(self, mock_get):
        """Test reverse_geocode_coordinates in app context."""
        # Mock the Google Maps API response
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

        # Call the function
        result = reverse_geocode_coordinates(37.7749, -122.4194)

        # Assert API was called with correct parameters
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["latlng"], "37.7749,-122.4194")
        self.assertEqual(kwargs["params"]["key"], "test_api_key")

        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(result["formatted_address"], "123 Main St, San Francisco, CA 94105, USA")
        self.assertEqual(result["quality"], "high")

    @patch("app.utils.geocoding.requests.get")
    def test_geocoding_error_handling_integration(self, mock_get):
        """Test error handling in geocoding functions with app context."""
        # Set API key to None to test configuration error
        self.app.config["MAPS_API_KEY"] = None

        # Test geocode_address with no API key
        result_geocode = geocode_address("123 Main St")
        self.assertFalse(result_geocode["success"])
        self.assertEqual(result_geocode["error"], "Geocoding service not configured")

        # Test reverse_geocode_coordinates with no API key
        result_reverse = reverse_geocode_coordinates(37.7749, -122.4194)
        self.assertFalse(result_reverse["success"])
        self.assertEqual(result_reverse["error"], "Geocoding service not configured")

        # Restore API key for next tests
        self.app.config["MAPS_API_KEY"] = "test_api_key"

        # Mock API error
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "INVALID_REQUEST", "error_message": "Invalid request"}
        mock_get.return_value = mock_response

        # Test geocode_address with API error
        result_geocode = geocode_address("invalid address")
        self.assertFalse(result_geocode["success"])
        self.assertEqual(result_geocode["error"], "Geocoding failed: INVALID_REQUEST")

        # Test reverse_geocode_coordinates with API error
        result_reverse = reverse_geocode_coordinates(999, 999)
        self.assertFalse(result_reverse["success"])
        self.assertEqual(result_reverse["error"], "Reverse geocoding failed: INVALID_REQUEST")
