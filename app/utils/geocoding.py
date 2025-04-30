import logging
import os
import re
from typing import Any, Dict, Optional, Tuple, Union

import requests
from flask import current_app

logger = logging.getLogger(__name__)

GEOCODING_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"


def validate_address(address: str) -> Dict[str, Union[bool, str]]:
    """
    Validate if an address is likely to be complete.

    Args:
        address: The address string to validate

    Returns:
        A dictionary containing:
            valid: Boolean indicating if the address appears to be valid
            message: Validation message (if invalid)
    """
    if not address or not address.strip():
        return {"valid": False, "message": "Address cannot be empty"}

    # Check for minimum length
    if len(address.strip()) < 5:
        return {"valid": False, "message": "Address is too short"}

    # Check for common address components using regex
    # This is a basic check and not a replacement for geocoding validation
    address_contains_number = bool(re.search(r"\d", address))
    address_contains_street = bool(
        re.search(
            r"\b(street|st\.?|avenue|ave\.?|road|rd\.?|boulevard|blvd\.?|lane|ln\.?|drive|dr\.?|way|court|ct\.?|plaza|square|sq\.?|parkway|pkwy\.?|place|pl\.?)\b",
            address,
            re.IGNORECASE,
        )
    )

    if not address_contains_number:
        return {"valid": False, "message": "Address should include a street number"}

    if not address_contains_street:
        return {"valid": False, "message": "Address should include a street name"}

    # Basic check for city/state or zip
    has_city_state = bool(re.search(r",\s*([A-Za-z\s]+)", address))
    has_zip = bool(re.search(r"\b\d{5}(?:-\d{4})?\b", address))

    if not (has_city_state or has_zip):
        return {"valid": False, "message": "Address should include city, state, or postal code"}

    return {"valid": True, "message": "Address appears valid"}


def reverse_geocode_coordinates(lat: float, lng: float, api_key: str = None) -> Dict[str, Any]:
    """
    Reverse geocode coordinates to an address using Google Maps API.

    Args:
        lat: Latitude
        lng: Longitude
        api_key: Google Maps API key (defaults to environment variable if not provided)

    Returns:
        Dict with reverse geocoding results including success status, address if successful,
        or error message if unsuccessful
    """
    # Validate inputs
    if not _validate_coordinates(lat, lng):
        return {"success": False, "error": "Invalid latitude/longitude values"}

    # Get API key if not provided
    if not api_key:
        api_key = current_app.config.get("GOOGLE_MAPS_API_KEY") or current_app.config.get("MAPS_API_KEY")
        if not api_key:
            return {"success": False, "error": "Geocoding service not configured"}
    elif api_key == "":
        return {"success": False, "error": "API key cannot be empty"}

    try:
        # Make the request to Google Maps API
        params = {"latlng": f"{lat},{lng}", "key": api_key}
        response = requests.get(GEOCODING_API_URL, params=params)
        data = response.json()

        # Check for API errors
        if data["status"] != "OK":
            if data["status"] == "ZERO_RESULTS":
                return {"success": False, "error": "Reverse geocoding failed: ZERO_RESULTS"}
            error_message = data.get("error_message", f"Reverse geocoding failed: {data['status']}")
            return {"success": False, "error": error_message}

        # Check if we have results
        if not data.get("results"):
            return {"success": False, "error": "No results found for the given coordinates"}

        # Extract the first result (most relevant)
        result = data["results"][0]

        # Determine quality of the result based on the types
        quality = _determine_address_quality(result)

        return {"success": True, "formatted_address": result["formatted_address"], "quality": quality}

    except Exception as e:
        logger.error(f"Error during reverse geocoding: {str(e)}", exc_info=True)
        return {"success": False, "error": f"Reverse geocoding service error: {str(e)}"}


def _validate_coordinates(lat: float, lng: float) -> bool:
    """
    Validate that latitude and longitude are within valid ranges.

    Args:
        lat: Latitude (-90 to 90)
        lng: Longitude (-180 to 180)

    Returns:
        True if coordinates are valid, False otherwise
    """
    try:
        lat_float = float(lat)
        lng_float = float(lng)
        return -90 <= lat_float <= 90 and -180 <= lng_float <= 180
    except (ValueError, TypeError):
        return False


def _determine_address_quality(result: Dict[str, Any]) -> str:
    """
    Determine the quality of a geocoding result based on its types.

    Args:
        result: A geocoding result from Google Maps API

    Returns:
        String quality level: "high", "medium", or "low"
    """
    types = result.get("types", [])

    # High precision results have specific address information
    high_precision_types = ["street_address", "premise", "subpremise", "point_of_interest"]

    # Medium precision results have neighborhood or locality information
    medium_precision_types = ["neighborhood", "locality", "sublocality", "postal_code", "route"]

    if any(t in types for t in high_precision_types):
        return "high"
    elif any(t in types for t in medium_precision_types):
        return "medium"
    else:
        return "low"


def geocode_address(address: str, api_key: str = None) -> Dict[str, Any]:
    """
    Geocode an address string to latitude and longitude using Google Maps API.

    Args:
        address: The address to geocode
        api_key: Google Maps API key (defaults to environment variable if not provided)

    Returns:
        Dict with geocoding results including success status, lat/lng if successful,
        or error message if unsuccessful
    """
    # Validate inputs
    if not address:
        return {"success": False, "error": "No address provided"}

    # Get API key if not provided
    if not api_key:
        api_key = current_app.config.get("GOOGLE_MAPS_API_KEY") or current_app.config.get("MAPS_API_KEY")
        if not api_key:
            return {"success": False, "error": "Geocoding service not configured"}
    elif api_key == "":
        return {"success": False, "error": "API key cannot be empty"}

    try:
        # Make the request to Google Maps API
        params = {"address": address, "key": api_key}
        response = requests.get(GEOCODING_API_URL, params=params)
        data = response.json()

        # Check for API errors
        if data["status"] != "OK":
            if data["status"] == "ZERO_RESULTS":
                return {"success": False, "error": "ZERO_RESULTS"}
            # Use the error_message directly from API if available
            error_message = data.get("error_message", f"Geocoding failed: {data['status']}")
            return {"success": False, "error": error_message}

        # Check if we have results
        if not data.get("results"):
            return {"success": False, "error": "No results found for the given address"}

        # Extract the first result (most relevant)
        result = data["results"][0]
        location = result["geometry"]["location"]

        # Determine quality based on types
        quality = _determine_address_quality(result)

        result = {
            "success": True,
            "lat": location["lat"],
            "lng": location["lng"],
            "formatted_address": result["formatted_address"],
            "quality": quality,
        }

        # Add coordinates in the format expected by the tests
        result["coordinates"] = {"lat": location["lat"], "lng": location["lng"]}

        return result

    except Exception as e:
        logger.error(f"Error during geocoding: {str(e)}", exc_info=True)
        return {"success": False, "error": f"Error during geocoding: {str(e)}"}
