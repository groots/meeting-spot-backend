import logging
import re
from typing import Dict, Optional, Tuple, Union

import requests
from flask import current_app

logger = logging.getLogger(__name__)


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


def reverse_geocode_coordinates(lat: float, lng: float) -> Dict[str, Union[bool, str]]:
    """
    Convert latitude and longitude coordinates to a readable address using Google Maps Geocoding API.

    Args:
        lat: The latitude coordinate
        lng: The longitude coordinate

    Returns:
        A dictionary containing:
            success: Boolean indicating if reverse geocoding was successful
            formatted_address: The readable address (if successful)
            error: Error message (if not successful)
    """
    logger.info(f"Reverse geocoding coordinates: ({lat}, {lng})")

    # Get API key from config
    api_key = current_app.config.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        logger.error("Google Maps API key not configured")
        return {"success": False, "error": "Geocoding service not configured"}

    # Google Maps Geocoding API endpoint
    url = "https://maps.googleapis.com/maps/api/geocode/json"

    try:
        # Make request to Google Maps Geocoding API with latlng parameter
        logger.info(f"Sending reverse geocoding request to Google Maps API for coordinates: ({lat}, {lng})")
        response = requests.get(url, params={"latlng": f"{lat},{lng}", "key": api_key})
        response.raise_for_status()  # Raise exception for HTTP errors

        data = response.json()
        logger.debug(f"Google API response status: {data['status']}")

        # Check if request was successful
        if data["status"] != "OK":
            logger.error(f"Reverse geocoding error: {data['status']}")
            if "error_message" in data:
                logger.error(f"Error message: {data['error_message']}")
            return {"success": False, "error": f"Reverse geocoding failed: {data.get('status')}"}

        # Get the first result (most relevant)
        if not data["results"]:
            logger.warning("No results found from Google API")
            return {"success": False, "error": "No address found for the provided coordinates"}

        # Find the most appropriate address result
        best_result = data["results"][0]
        formatted_address = best_result["formatted_address"]

        # Look for a result that contains a street address if available
        for result in data["results"]:
            address_types = result.get("types", [])
            if "street_address" in address_types or "route" in address_types or "premise" in address_types:
                formatted_address = result["formatted_address"]
                best_result = result
                break

        logger.info(f"Reverse geocoded ({lat}, {lng}) to address: {formatted_address}")

        # Determine address quality
        address_components = best_result.get("address_components", [])
        component_types = [comp.get("types", []) for comp in address_components]
        all_types = [t for sublist in component_types for t in sublist]

        # Check if essential components are present
        has_street_number = "street_number" in all_types
        has_route = "route" in all_types
        has_locality = "locality" in all_types or "administrative_area_level_1" in all_types

        address_quality = (
            "high"
            if (has_street_number and has_route and has_locality)
            else "medium"
            if (has_route and has_locality)
            else "low"
        )

        logger.info(f"Address quality: {address_quality}")

        return {
            "success": True,
            "formatted_address": formatted_address,
            "quality": address_quality,
        }

    except Exception as e:
        logger.error(f"Error calling Google Maps Reverse Geocoding API: {str(e)}")
        return {"success": False, "error": f"Reverse geocoding service error: {str(e)}"}


def geocode_address(address: str) -> Dict[str, Union[bool, Dict[str, float], str]]:
    """
    Convert an address string to latitude and longitude coordinates using Google Maps Geocoding API.

    Args:
        address: The address string to geocode

    Returns:
        A dictionary containing:
            success: Boolean indicating if geocoding was successful
            coordinates: Dictionary with 'lat' and 'lng' keys (if successful)
            formatted_address: Formatted address from Google (if successful)
            error: Error message (if not successful)
    """
    logger.info(f"Geocoding address: '{address}'")

    if not address or not address.strip():
        logger.warning("Empty address provided to geocode_address")
        return {"success": False, "error": "No address provided"}

    # First validate the address format
    validation = validate_address(address)
    if not validation["valid"]:
        logger.warning(f"Address validation failed: {validation['message']}")
        return {"success": False, "error": validation["message"]}

    # Get API key from config
    api_key = current_app.config.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        logger.error("Google Maps API key not configured")
        return {"success": False, "error": "Geocoding service not configured"}

    # Google Maps Geocoding API endpoint
    url = "https://maps.googleapis.com/maps/api/geocode/json"

    try:
        # Make request to Google Maps Geocoding API
        logger.info(f"Sending request to Google Maps API for address: '{address}'")
        response = requests.get(url, params={"address": address, "key": api_key})
        response.raise_for_status()  # Raise exception for HTTP errors

        data = response.json()
        logger.debug(f"Google API response status: {data['status']}")

        # Check if request was successful
        if data["status"] != "OK":
            logger.error(f"Geocoding error: {data['status']}")
            if "error_message" in data:
                logger.error(f"Error message: {data['error_message']}")
            return {"success": False, "error": f"Geocoding failed: {data.get('status')}"}

        # Get the first result (most relevant)
        if not data["results"]:
            logger.warning("No results found from Google API")
            return {"success": False, "error": "No results found for the provided address"}

        result = data["results"][0]
        location = result["geometry"]["location"]
        logger.info(f"Geocoded '{address}' to coordinates: ({location['lat']}, {location['lng']})")

        # Check if the address is a partial match
        if result.get("partial_match", False):
            logger.warning(f"Partial match found for address: {address}")
            # Still return results but add a warning in logs

        # Determine address quality by checking address components
        address_components = result.get("address_components", [])
        component_types = [comp.get("types", []) for comp in address_components]
        all_types = [t for sublist in component_types for t in sublist]

        # Check if essential components are present
        has_street_number = "street_number" in all_types
        has_route = "route" in all_types
        has_locality = "locality" in all_types or "administrative_area_level_1" in all_types

        address_quality = (
            "high"
            if (has_street_number and has_route and has_locality)
            else "medium"
            if (has_route and has_locality)
            else "low"
        )

        logger.info(f"Address quality: {address_quality}")

        return {
            "success": True,
            "coordinates": {"lat": location["lat"], "lng": location["lng"]},
            "formatted_address": result["formatted_address"],
            "quality": address_quality,
        }

    except Exception as e:
        logger.error(f"Error calling Google Maps Geocoding API: {str(e)}")
        return {"success": False, "error": f"Geocoding service error: {str(e)}"}
