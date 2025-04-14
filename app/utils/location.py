import json
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

import requests
from flask import current_app

logger = logging.getLogger(__name__)

# Place category definitions - mapping UI categories to Google Places API types
PLACE_CATEGORIES = {
    "Accommodation": ["lodging", "hotel", "campground", "rv_park"],
    "Food & Drink": ["restaurant", "cafe", "bakery", "bar", "meal_takeaway", "meal_delivery"],
    "Night Life": ["bar", "night_club", "casino"],
    "Fun & Family": ["amusement_park", "aquarium", "park", "bowling_alley", "movie_theater", "zoo"],
    "Cultural": ["museum", "art_gallery", "library", "tourist_attraction", "place_of_worship"],
    "Shopping": ["shopping_mall", "department_store", "supermarket", "clothing_store", "electronics_store"],
    "Transport": ["transit_station", "train_station", "subway_station", "bus_station", "airport"],
}

# Define subcategories with filtering criteria
FOOD_SUBCATEGORIES = {
    "fine dining": {
        "min_price_level": 3,
        "min_rating": 4.0,
        "types": ["restaurant"],
        "keywords": ["fine dining", "upscale", "gourmet"],
    },
    "hole in the wall": {
        "max_price_level": 2,
        "min_rating": 3.0,
        "max_rating": 4.5,
        "types": ["restaurant", "cafe", "meal_takeaway"],
        "keywords": ["local", "authentic", "hidden gem"],
    },
    "cheap eats": {
        "max_price_level": 1,
        "min_rating": 3.5,
        "types": ["restaurant", "cafe", "meal_takeaway", "meal_delivery"],
        "keywords": ["cheap", "affordable", "budget"],
    },
    "vegetarian": {"types": ["restaurant", "cafe"], "keywords": ["vegetarian", "vegan", "plant based"]},
    "outdoor seating": {
        "types": ["restaurant", "cafe", "bar"],
        "keywords": ["outdoor", "patio", "terrace", "alfresco"],
    },
    "quick bite": {
        "max_price_level": 2,
        "types": ["fast_food", "cafe", "meal_takeaway"],
        "keywords": ["fast", "quick", "express"],
    },
}


def calculate_midpoint(lat1: float, lon1: float, lat2: float, lon2: float) -> Tuple[float, float]:
    """
    Calculate the midpoint between two geographic coordinates.
    Uses the Haversine formula to find a point equidistant between two locations.

    Args:
        lat1: Latitude of first point in decimal degrees
        lon1: Longitude of first point in decimal degrees
        lat2: Latitude of second point in decimal degrees
        lon2: Longitude of second point in decimal degrees

    Returns:
        Tuple of (latitude, longitude) for the midpoint
    """
    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Calculate differences
    d_lon = lon2_rad - lon1_rad

    # Calculate intermediate values
    Bx = math.cos(lat2_rad) * math.cos(d_lon)
    By = math.cos(lat2_rad) * math.sin(d_lon)

    # Calculate the midpoint
    lat3_rad = math.atan2(math.sin(lat1_rad) + math.sin(lat2_rad), math.sqrt((math.cos(lat1_rad) + Bx) ** 2 + By**2))
    lon3_rad = lon1_rad + math.atan2(By, math.cos(lat1_rad) + Bx)

    # Convert back to degrees
    lat3 = math.degrees(lat3_rad)
    lon3 = math.degrees(lon3_rad)

    return (lat3, lon3)


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the distance between two points on Earth using the Haversine formula.

    Args:
        lat1: Latitude of first point in decimal degrees
        lon1: Longitude of first point in decimal degrees
        lat2: Latitude of second point in decimal degrees
        lon2: Longitude of second point in decimal degrees

    Returns:
        Distance in kilometers
    """
    # Earth's radius in kilometers
    R = 6371.0

    # Convert from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Differences
    d_lat = lat2_rad - lat1_rad
    d_lon = lon2_rad - lon1_rad

    # Haversine formula
    a = math.sin(d_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(d_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c

    return distance


def get_place_types_for_category(category: str) -> List[str]:
    """
    Convert a user-friendly category to Google Places API place types.

    Args:
        category: The user-friendly category (e.g., "Food & Drink", "fine dining")

    Returns:
        List of Google Places API type strings
    """
    # Check if it's a main category
    if category in PLACE_CATEGORIES:
        return PLACE_CATEGORIES[category]

    # Check if it's a food subcategory
    if category.lower() in FOOD_SUBCATEGORIES:
        return FOOD_SUBCATEGORIES[category.lower()]["types"]

    # Default to restaurant if no match
    logger.warning(f"Unrecognized category: {category}, defaulting to restaurant")
    return ["restaurant"]


def get_category_keywords(category: str) -> List[str]:
    """
    Get keywords associated with a specific category or subcategory.

    Args:
        category: The category or subcategory

    Returns:
        List of keywords or empty list if none defined
    """
    if category.lower() in FOOD_SUBCATEGORIES and "keywords" in FOOD_SUBCATEGORIES[category.lower()]:
        return FOOD_SUBCATEGORIES[category.lower()]["keywords"]
    return []


def find_meeting_spots(
    lat: float,
    lon: float,
    radius: int = 1000,
    category: str = "restaurant",
    subcategory: Optional[str] = None,
    max_results: int = 5,
) -> List[Dict[str, Any]]:
    """
    Find meeting spots near the provided coordinates using Google Places API.

    Args:
        lat: Latitude of the center point
        lon: Longitude of the center point
        radius: Search radius in meters (default 1000)
        category: The main category (e.g., "Food & Drink") (default "restaurant")
        subcategory: Optional subcategory for more specific filtering (e.g., "fine dining")
        max_results: Maximum number of results to return (default 5)

    Returns:
        List of meeting spot dictionaries with details
    """
    api_key = current_app.config.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        logger.error("Google Maps API key not found in configuration")
        return []

    # Determine place types to search for
    if subcategory:
        place_types = get_place_types_for_category(subcategory)
        keywords = get_category_keywords(subcategory)
    else:
        place_types = get_place_types_for_category(category)
        keywords = []

    # Select the first type for the API call (API only allows one type parameter)
    # We'll filter for other types in post-processing
    place_type = place_types[0] if place_types else "restaurant"

    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {"location": f"{lat},{lon}", "radius": radius, "type": place_type, "key": api_key}

    # Add keyword if available for better relevance
    if keywords and len(keywords) > 0:
        params["keyword"] = keywords[0]

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        if data["status"] != "OK":
            logger.error(f"Google Places API error: {data['status']}")
            if "error_message" in data:
                logger.error(f"Error message: {data['error_message']}")
            return []

        places = data.get("results", [])

        # Format and filter the results
        meeting_spots = []
        for place in places:
            # Skip if not all required fields are present
            if "geometry" not in place or "location" not in place["geometry"]:
                continue

            # Construct the photo URL if available
            photos = []
            if "photos" in place and place["photos"]:
                for photo in place["photos"][:2]:  # Get up to 2 photos
                    photo_ref = photo.get("photo_reference")
                    if photo_ref:
                        photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_ref}&key={api_key}"
                        photos.append(photo_url)

            # Calculate distance from midpoint
            place_lat = place["geometry"]["location"]["lat"]
            place_lon = place["geometry"]["location"]["lng"]
            distance = calculate_distance(lat, lon, place_lat, place_lon)

            # Apply subcategory filters if specified
            if subcategory and subcategory.lower() in FOOD_SUBCATEGORIES:
                filters = FOOD_SUBCATEGORIES[subcategory.lower()]

                # Check price level constraints
                if "min_price_level" in filters and "price_level" in place:
                    if place["price_level"] < filters["min_price_level"]:
                        continue
                if "max_price_level" in filters and "price_level" in place:
                    if place["price_level"] > filters["max_price_level"]:
                        continue

                # Check rating constraints
                if "min_rating" in filters and "rating" in place:
                    if place["rating"] < filters["min_rating"]:
                        continue
                if "max_rating" in filters and "rating" in place:
                    if place["rating"] > filters["max_rating"]:
                        continue

            meeting_spots.append(
                {
                    "name": place["name"],
                    "place_id": place["place_id"],
                    "address": place.get("vicinity", ""),
                    "location": {"lat": place_lat, "lng": place_lon},
                    "rating": place.get("rating"),
                    "user_ratings_total": place.get("user_ratings_total"),
                    "price_level": place.get("price_level"),
                    "photos": photos,
                    "distance": distance,  # in kilometers
                    "types": place.get("types", []),
                    "category": category,
                    "subcategory": subcategory,
                }
            )

        # Sort by rating (if available), then by distance
        meeting_spots.sort(key=lambda x: (-x.get("rating", 0), x["distance"]))

        return meeting_spots[:max_results]

    except requests.RequestException as e:
        logger.error(f"Error calling Google Places API: {str(e)}")
        return []


def process_meeting_request(meeting_request) -> bool:
    """
    Process a meeting request to find meeting spots between two locations.
    Updates the meeting request with suggestions and changes status to COMPLETED.

    Args:
        meeting_request: The MeetingRequest object to process

    Returns:
        Boolean indicating success or failure
    """
    from app.models.enums import MeetingRequestStatus

    try:
        # Ensure request has both locations
        if (
            not meeting_request.address_a_lat
            or not meeting_request.address_a_lon
            or not meeting_request.address_b_lat
            or not meeting_request.address_b_lon
        ):
            logger.error(f"Missing coordinates for meeting request {meeting_request.request_id}")
            meeting_request.status = MeetingRequestStatus.FAILED
            return False

        # Calculate the midpoint between the two locations
        midpoint_lat, midpoint_lon = calculate_midpoint(
            meeting_request.address_a_lat,
            meeting_request.address_a_lon,
            meeting_request.address_b_lat,
            meeting_request.address_b_lon,
        )

        # Log the calculated midpoint
        logger.info(f"Calculated midpoint: {midpoint_lat}, {midpoint_lon} for request {meeting_request.request_id}")

        # Parse location_type into main category and subcategory if applicable
        category = "Food & Drink"  # Default category
        subcategory = None

        if meeting_request.location_type:
            # Handle combined category/subcategory strings like "Food & Drink: fine dining"
            if ":" in meeting_request.location_type:
                parts = meeting_request.location_type.split(":", 1)
                category = parts[0].strip()
                subcategory = parts[1].strip() if len(parts) > 1 else None
            # Direct subcategory mapping for food
            elif meeting_request.location_type.lower() in FOOD_SUBCATEGORIES:
                category = "Food & Drink"
                subcategory = meeting_request.location_type.lower()
            # Main category mapping
            elif meeting_request.location_type in PLACE_CATEGORIES:
                category = meeting_request.location_type

        # Find meeting spots near the midpoint
        meeting_spots = find_meeting_spots(
            midpoint_lat,
            midpoint_lon,
            category=category,
            subcategory=subcategory,
            radius=1500,  # 1.5km radius
            max_results=10,
        )

        if not meeting_spots:
            logger.warning(f"No meeting spots found for request {meeting_request.request_id}")
            # Try with a larger radius and more generic type
            meeting_spots = find_meeting_spots(
                midpoint_lat, midpoint_lon, category=category, radius=3000, max_results=10  # 3km radius
            )

            if not meeting_spots:
                # Last resort: try with any establishment type
                meeting_spots = find_meeting_spots(
                    midpoint_lat, midpoint_lon, category="Food & Drink", radius=5000, max_results=10  # 5km radius
                )

                if not meeting_spots:
                    logger.error(f"Failed to find any meeting spots for request {meeting_request.request_id}")
                    meeting_request.status = MeetingRequestStatus.FAILED
                    return False

        # Store the results in the meeting request
        meeting_request.suggested_options = meeting_spots

        # Update the status to COMPLETED
        meeting_request.status = MeetingRequestStatus.COMPLETED

        return True

    except Exception as e:
        logger.exception(f"Error processing meeting request {meeting_request.request_id}: {str(e)}")
        meeting_request.status = MeetingRequestStatus.FAILED
        return False
