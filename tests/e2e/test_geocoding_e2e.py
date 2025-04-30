import json
import unittest
from unittest.mock import MagicMock, patch

from app import create_app
from app.utils.geocoding import geocode_address, reverse_geocode_coordinates


class TestGeocodingE2E(unittest.TestCase):
    """End-to-end tests for geocoding endpoints and functionality."""

    def setUp(self):
        """Set up test app configuration and client."""
        self.app = create_app("testing")
        self.app.config["MAPS_API_KEY"] = "test_api_key"
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        """Clean up after tests."""
        self.app_context.pop()

    @patch("app.utils.geocoding.requests.get")
    def test_geocode_address_endpoint(self, mock_get):
        """Test the geocode address endpoint."""
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

        # Test the new API endpoint
        response = self.client.get("/api/v1/geocoding/geocode?address=123 Main St, San Francisco, CA")

        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["coordinates"]["lat"], 37.7749)
        self.assertEqual(data["coordinates"]["lng"], -122.4194)
        self.assertEqual(data["formatted_address"], "123 Main St, San Francisco, CA 94105, USA")

        # Test the POST method as well
        mock_get.reset_mock()
        response = self.client.post(
            "/api/v1/geocoding/geocode",
            data=json.dumps({"address": "123 Main St, San Francisco, CA"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["coordinates"]["lat"], 37.7749)
        self.assertEqual(data["coordinates"]["lng"], -122.4194)

    @patch("app.utils.geocoding.requests.get")
    def test_reverse_geocode_endpoint(self, mock_get):
        """Test the reverse geocode endpoint."""
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

        # Test the GET method
        response = self.client.get("/api/v1/geocoding/reverse-geocode?lat=37.7749&lng=-122.4194")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["formatted_address"], "123 Main St, San Francisco, CA 94105, USA")

        # Test the POST method as well
        mock_get.reset_mock()
        response = self.client.post(
            "/api/v1/geocoding/reverse-geocode",
            data=json.dumps({"lat": 37.7749, "lng": -122.4194}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["formatted_address"], "123 Main St, San Francisco, CA 94105, USA")

    # Create a mock geocode test that directly checks the geocode_address function
    @patch("app.utils.geocoding.requests.get")
    def test_meeting_location_with_geocoding(self, mock_get):
        """Test geocoding for meeting locations using the geocode_address function directly."""
        # Setup the mock for the requests.get call inside geocode_address
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

        # Call geocode_address directly
        result = geocode_address("123 Main St, San Francisco, CA", "test_api_key")

        # Verify the results
        self.assertTrue(result["success"])
        self.assertEqual(result["lat"], 37.7749)
        self.assertEqual(result["lng"], -122.4194)
        self.assertEqual(result["formatted_address"], "123 Main St, San Francisco, CA 94105, USA")

        # Verify the API was called with the correct parameters
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["address"], "123 Main St, San Francisco, CA")
        self.assertEqual(kwargs["params"]["key"], "test_api_key")

    def test_invalid_geocode_requests(self):
        """Test validation of invalid geocode requests."""
        # Test missing address
        response = self.client.post("/api/v1/geocoding/geocode", data=json.dumps({}), content_type="application/json")
        self.assertEqual(response.status_code, 400)

        # Test missing coordinates
        response = self.client.post(
            "/api/v1/geocoding/reverse-geocode",
            data=json.dumps({"lat": 37.7749}),
            content_type="application/json",  # Missing lng
        )
        self.assertEqual(response.status_code, 400)

        # Test invalid coordinate values
        response = self.client.post(
            "/api/v1/geocoding/reverse-geocode",
            data=json.dumps({"lat": "invalid", "lng": -122.4194}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
