import math
from unittest.mock import MagicMock, patch

import pytest

from app.utils.location import (
    calculate_distance,
    calculate_midpoint,
    find_meeting_spots,
    get_category_keywords,
    get_place_types_for_category,
    process_meeting_request,
)


def test_calculate_midpoint():
    """Test midpoint calculation with known coordinates."""
    # San Francisco and New York coordinates
    sf_lat, sf_lon = 37.7749, -122.4194
    ny_lat, ny_lon = 40.7128, -74.0060

    # Calculate midpoint
    midpoint_lat, midpoint_lon = calculate_midpoint(sf_lat, sf_lon, ny_lat, ny_lon)

    # The midpoint should be roughly in the middle of the US
    # (not exactly halfway in terms of lat/lon due to earth's curvature)
    assert 35 < midpoint_lat < 45
    assert -110 > midpoint_lon > -95

    # Test with same points (should return the same point)
    same_lat, same_lon = calculate_midpoint(sf_lat, sf_lon, sf_lat, sf_lon)
    assert math.isclose(same_lat, sf_lat, abs_tol=0.0001)
    assert math.isclose(same_lon, sf_lon, abs_tol=0.0001)


def test_calculate_distance():
    """Test distance calculation using known distances."""
    # San Francisco and New York coordinates
    sf_lat, sf_lon = 37.7749, -122.4194
    ny_lat, ny_lon = 40.7128, -74.0060

    # The distance should be approximately 4,130 km
    distance = calculate_distance(sf_lat, sf_lon, ny_lat, ny_lon)
    assert 4000 < distance < 4200

    # Test zero distance
    zero_distance = calculate_distance(sf_lat, sf_lon, sf_lat, sf_lon)
    assert math.isclose(zero_distance, 0, abs_tol=0.0001)


def test_get_place_types_for_category():
    """Test mapping categories to place types."""
    # Test main categories
    assert "restaurant" in get_place_types_for_category("Food & Drink")
    assert "night_club" in get_place_types_for_category("Night Life")
    assert "museum" in get_place_types_for_category("Cultural")

    # Test subcategories
    assert "restaurant" in get_place_types_for_category("fine dining")
    assert "cafe" in get_place_types_for_category("cheap eats")

    # Test unknown category (should default to restaurant)
    assert get_place_types_for_category("unknown") == ["restaurant"]


def test_get_category_keywords():
    """Test getting keywords for subcategories."""
    # Test subcategories with keywords
    fine_dining_keywords = get_category_keywords("fine dining")
    assert "upscale" in fine_dining_keywords

    hole_in_wall_keywords = get_category_keywords("hole in the wall")
    assert "authentic" in hole_in_wall_keywords

    # Test unknown category (should return empty list)
    assert get_category_keywords("unknown") == []


@patch("app.utils.location.requests.get")
@patch("flask.current_app")
def test_find_meeting_spots(mock_current_app, mock_requests_get):
    """Test finding meeting spots with mocked Google Places API."""
    # Mock the API key
    mock_current_app.config.get.return_value = "fake_api_key"

    # Mock the API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "OK",
        "results": [
            {
                "name": "Test Restaurant 1",
                "place_id": "place123",
                "vicinity": "123 Test St",
                "geometry": {"location": {"lat": 37.78, "lng": -122.41}},
                "rating": 4.5,
                "price_level": 2,
                "photos": [{"photo_reference": "photo123"}],
                "types": ["restaurant", "food"],
            },
            {
                "name": "Test Cafe",
                "place_id": "place456",
                "vicinity": "456 Test Ave",
                "geometry": {"location": {"lat": 37.79, "lng": -122.42}},
                "rating": 4.0,
                "price_level": 1,
                "photos": [{"photo_reference": "photo456"}],
                "types": ["cafe", "restaurant", "food"],
            },
        ],
    }
    mock_response.status_code = 200
    mock_requests_get.return_value = mock_response

    # Test finding meeting spots
    results = find_meeting_spots(37.78, -122.41, category="Food & Drink")

    # Check request was made correctly
    args, kwargs = mock_requests_get.call_args
    assert "maps.googleapis.com" in kwargs["url"]
    assert kwargs["params"]["location"] == "37.78,-122.41"
    assert kwargs["params"]["type"] in ["restaurant", "cafe", "bar", "meal_takeaway", "meal_delivery"]

    # Check results are formatted correctly
    assert len(results) == 2
    assert results[0]["name"] == "Test Restaurant 1"
    assert results[0]["rating"] == 4.5
    assert results[0]["price_level"] == 2
    assert "photo123" in results[0]["photos"][0]

    # Test with subcategory
    find_meeting_spots(37.78, -122.41, category="Food & Drink", subcategory="fine dining")
    args, kwargs = mock_requests_get.call_args
    assert kwargs["params"]["type"] == "restaurant"
    assert "keyword" in kwargs["params"]
    assert kwargs["params"]["keyword"] in ["fine dining", "upscale", "gourmet"]


@patch("app.utils.location.find_meeting_spots")
def test_process_meeting_request(mock_find_meeting_spots):
    """Test processing a meeting request with mocked spot finder."""
    # Mock the MeetingRequest and dependencies
    from app.models.enums import MeetingRequestStatus

    class MockMeetingRequest:
        def __init__(self):
            self.request_id = "test123"
            self.address_a_lat = 37.7749
            self.address_a_lon = -122.4194
            self.address_b_lat = 40.7128
            self.address_b_lon = -74.0060
            self.location_type = "Food & Drink: fine dining"
            self.status = MeetingRequestStatus.CALCULATING
            self.suggested_options = None

    # Mock finding spots
    mock_spots = [{"name": "Test Restaurant", "rating": 4.5}]
    mock_find_meeting_spots.return_value = mock_spots

    # Process the request
    meeting_request = MockMeetingRequest()
    result = process_meeting_request(meeting_request)

    # Check the result
    assert result is True
    assert meeting_request.status == MeetingRequestStatus.COMPLETED
    assert meeting_request.suggested_options == mock_spots

    # Test with missing coordinates
    meeting_request = MockMeetingRequest()
    meeting_request.address_b_lat = None
    result = process_meeting_request(meeting_request)
    assert result is False
    assert meeting_request.status == MeetingRequestStatus.FAILED

    # Test with no meeting spots found
    meeting_request = MockMeetingRequest()
    mock_find_meeting_spots.return_value = []
    # Configure mock to return empty list first time, then non-empty list on subsequent calls
    mock_find_meeting_spots.side_effect = [[], [], mock_spots]
    result = process_meeting_request(meeting_request)
    assert result is True  # Should succeed on third attempt
    assert meeting_request.status == MeetingRequestStatus.COMPLETED
