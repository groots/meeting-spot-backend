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
        """Test geocoding error handling in app context."""
        # Mock Google Maps API with an error response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "INVALID_REQUEST",
        }
        mock_get.return_value = mock_response

        # Test geocoding with bad input
        result = geocode_address("bad input")

        # Verify error is properly formatted
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Geocoding failed: INVALID_REQUEST")
