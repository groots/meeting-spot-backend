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

    @patch("app.utils.geocoding.requests.get")
    def test_meeting_location_with_geocoding(self, mock_get):
        """Test creating a meeting with location geocoding."""
        # Mock the Google Maps API response for geocoding
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

        # Create a test user and get auth token
        # Note: This would normally use the actual auth flow, but we'll mock it for this test
        auth_headers = {"Authorization": "Bearer test_token"}

        # Mock the geocoding service directly
        with patch("app.api.meeting_requests.geocode_address") as mock_geocode:
            # Set up mock return value for geocode_address
            mock_geocode.return_value = {
                "success": True,
                "lat": 37.7749,
                "lng": -122.4194,
                "formatted_address": "123 Main St, San Francisco, CA 94105, USA",
                "quality": "high",
                "coordinates": {"lat": 37.7749, "lng": -122.4194},
            }

            # Make a request to create a meeting with location
            meeting_data = {
                "user_b_contact": "test@example.com",
                "location_type": "Restaurant",
                "address_a": "123 Main St, San Francisco, CA",
            }

            response = self.client.post(
                "/api/v1/meeting-requests",
                data=json.dumps(meeting_data),
                content_type="application/json",
                headers=auth_headers,
            )

            # Check that the geocoding function was called
            mock_geocode.assert_called_once()
            args = mock_geocode.call_args[0]
            self.assertEqual(args[0], "123 Main St, San Francisco, CA")

            # Check for successful response
            self.assertEqual(response.status_code, 201)

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
