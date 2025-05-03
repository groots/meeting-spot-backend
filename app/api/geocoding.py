from flask import Blueprint, current_app, request
from flask_restx import Api, Namespace, Resource, fields

from app.utils.geocoding import geocode_address, reverse_geocode_coordinates, validate_address

# Create Flask blueprint
geocoding_bp = Blueprint("geocoding", __name__)

# Initialize Flask-RestX API
api_restx = Api(
    geocoding_bp,
    version="1.0",
    title="Geocoding API",
    description="API for geocoding operations",
    doc="/docs",
    prefix="",  # Empty prefix since the blueprint already has a prefix
)

# Create geocoding namespace
api = api_restx.namespace("", description="Geocoding operations")

# Define geocoding response model
geocoding_response = api.model(
    "GeocodingResponse",
    {
        "success": fields.Boolean(description="Indicates if geocoding was successful"),
        "coordinates": fields.Nested(
            api.model(
                "Coordinates",
                {
                    "lat": fields.Float(description="Latitude"),
                    "lng": fields.Float(description="Longitude"),
                },
            ),
            skip_none=True,
            description="Latitude and longitude coordinates",
        ),
        "formatted_address": fields.String(description="Formatted address from Google"),
        "quality": fields.String(description="Address quality assessment (high, medium, low)"),
        "error": fields.String(description="Error message if geocoding failed"),
    },
)

# Define address validation response model
validation_response = api.model(
    "ValidationResponse",
    {
        "valid": fields.Boolean(description="Indicates if address appears valid"),
        "message": fields.String(description="Validation message"),
    },
)

# Define geocoding request model
geocoding_request = api.model(
    "GeocodingRequest",
    {
        "address": fields.String(required=False, description="Address to geocode"),
        "lat": fields.Float(required=False, description="Latitude for reverse geocoding"),
        "lng": fields.Float(required=False, description="Longitude for reverse geocoding"),
        "skip_reverse": fields.Boolean(
            required=False, description="Skip reverse geocoding for 'Location (lat, lng)' format"
        ),
    },
)


@api.route("")
class GeocodingResource(Resource):
    @api.doc("geocode_address_or_coordinates")
    @api.expect(geocoding_request)
    @api.marshal_with(geocoding_response)
    @api.response(200, "Geocoding successful")
    @api.response(400, "Invalid request")
    @api.response(500, "Server error")
    def post(self):
        """Geocode an address to coordinates or reverse geocode coordinates to an address"""
        try:
            data = request.get_json()
            current_app.logger.info(f"Geocoding request received: {data}")

            if not data:
                current_app.logger.error("No JSON data in request")
                return {"success": False, "error": "No data provided"}, 400

            # Check if reverse geocoding should be skipped (optimization flag)
            skip_reverse = data.get("skip_reverse", False)

            # Check if this is a reverse geocoding request (lat/lng provided)
            if "lat" in data and "lng" in data:
                lat = data.get("lat")
                lng = data.get("lng")

                # Validate the coordinates
                if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
                    return {"success": False, "error": "Invalid coordinates format"}, 400

                current_app.logger.info(f"Processing reverse geocoding request for coordinates: ({lat}, {lng})")

                if skip_reverse:
                    # Skip reverse geocoding and just return the coordinates with a formatted string
                    return {
                        "success": True,
                        "coordinates": {"lat": lat, "lng": lng},
                        "formatted_address": f"Location ({lat}, {lng})",
                        "quality": "high",
                    }, 200

                # Perform reverse geocoding
                result = reverse_geocode_coordinates(lat, lng)
                current_app.logger.info(f"Reverse geocoding result: {result}")

                if not result["success"]:
                    # If reverse geocoding failed, still return the coordinates with a formatted string
                    return {
                        "success": True,
                        "coordinates": {"lat": lat, "lng": lng},
                        "formatted_address": f"Location ({lat}, {lng})",
                        "quality": "medium",
                    }, 200

                # Add the coordinates to the result
                result["coordinates"] = {"lat": lat, "lng": lng}
                return result, 200

            # Forward geocoding
            elif "address" in data:
                address = data.get("address", "").strip()

                # Validate the address
                if not address:
                    return {"success": False, "error": "Address cannot be empty"}, 400

                current_app.logger.info(f"Processing geocoding request for address: {address}")

                # Check if this could be coordinates in a string format
                coords_pattern = r"^\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*$"
                import re

                coords_match = re.match(coords_pattern, address)
                if coords_match:
                    try:
                        lat = float(coords_match.group(1))
                        lng = float(coords_match.group(2))

                        # Perform reverse geocoding to get the address
                        reverse_result = reverse_geocode_coordinates(lat, lng)
                        current_app.logger.info(f"Parsed coordinates from string: ({lat}, {lng})")
                        current_app.logger.info(f"Reverse geocoding result: {reverse_result}")

                        if reverse_result["success"]:
                            # Return both the coordinates and the reverse geocoded address
                            return {
                                "success": True,
                                "coordinates": {"lat": lat, "lng": lng},
                                "formatted_address": reverse_result["formatted_address"],
                                "quality": reverse_result.get("quality", "high"),
                            }, 200
                        else:
                            # If reverse geocoding fails, just return the coordinates
                            return {
                                "success": True,
                                "coordinates": {"lat": lat, "lng": lng},
                                "formatted_address": address,  # Use original string
                                "quality": "high",  # Direct coordinates are considered high quality
                            }, 200
                    except (ValueError, IndexError):
                        # Not valid coordinates, continue with normal geocoding
                        pass

                # Normal forward geocoding
                result = geocode_address(address)
                current_app.logger.info(f"Geocoding result: {result}")

                if not result["success"]:
                    # If geocoding failed, return a 400 status code
                    return result, 400

                return result, 200

            else:
                current_app.logger.error("No address or coordinates provided in request")
                return {"success": False, "error": "Either address or lat/lng must be provided"}, 400

        except Exception as e:
            current_app.logger.exception(f"Error in geocoding endpoint: {str(e)}")
            return {"success": False, "error": f"Server error: {str(e)}"}, 500

    # Add GET method for geocoding
    @api.doc("geocode_address_or_coordinates_get")
    @api.marshal_with(geocoding_response)
    @api.response(200, "Geocoding successful")
    @api.response(400, "Invalid request")
    @api.response(500, "Server error")
    def get(self):
        """GET method for geocoding to support the tests"""
        try:
            # Get parameters from query string
            address = request.args.get("address")
            lat = request.args.get("lat")
            lng = request.args.get("lng")

            # Create a data structure similar to what the POST method expects
            data = {}
            if address:
                data["address"] = address
            if lat and lng:
                try:
                    data["lat"] = float(lat)
                    data["lng"] = float(lng)
                except ValueError:
                    return {"success": False, "error": "Invalid coordinates format"}, 400

            # Check if we have the necessary data
            if not data:
                return {"success": False, "error": "No query parameters provided"}, 400

            # Handle reverse geocoding
            if "lat" in data and "lng" in data:
                result = reverse_geocode_coordinates(data["lat"], data["lng"])
                if result["success"]:
                    result["coordinates"] = {"lat": data["lat"], "lng": data["lng"]}
                return result, 200

            # Handle forward geocoding
            elif "address" in data:
                result = geocode_address(data["address"])
                return result, 200 if result["success"] else 400

            else:
                return {"success": False, "error": "Either address or lat/lng must be provided"}, 400

        except Exception as e:
            current_app.logger.exception(f"Error in geocoding GET endpoint: {str(e)}")
            return {"success": False, "error": f"Server error: {str(e)}"}, 500


# Add separate routes to match the test expectations
@api.route("/geocode")
class GeocodingForwardResource(Resource):
    @api.doc("geocode_address")
    @api.expect(geocoding_request)
    @api.marshal_with(geocoding_response)
    @api.response(200, "Geocoding successful")
    @api.response(400, "Invalid request")
    @api.response(500, "Server error")
    def post(self):
        """Geocode an address to coordinates"""
        try:
            data = request.get_json()
            if not data or "address" not in data:
                return {"success": False, "error": "Address is required"}, 400

            address = data.get("address", "").strip()
            if not address:
                return {"success": False, "error": "Address cannot be empty"}, 400

            result = geocode_address(address)
            return result, 200 if result["success"] else 400
        except Exception as e:
            current_app.logger.exception(f"Error in geocode endpoint: {str(e)}")
            return {"success": False, "error": f"Server error: {str(e)}"}, 500

    def get(self):
        """GET method for forward geocoding"""
        try:
            address = request.args.get("address")
            if not address:
                return {"success": False, "error": "Address is required"}, 400

            result = geocode_address(address)
            return result, 200 if result["success"] else 400
        except Exception as e:
            current_app.logger.exception(f"Error in geocode GET endpoint: {str(e)}")
            return {"success": False, "error": f"Server error: {str(e)}"}, 500


@api.route("/reverse-geocode")
class GeocodingReverseResource(Resource):
    @api.doc("reverse_geocode_coordinates")
    @api.expect(geocoding_request)
    @api.marshal_with(geocoding_response)
    @api.response(200, "Reverse geocoding successful")
    @api.response(400, "Invalid request")
    @api.response(500, "Server error")
    def post(self):
        """Reverse geocode coordinates to an address"""
        try:
            data = request.get_json()
            if not data or "lat" not in data or "lng" not in data:
                return {"success": False, "error": "Latitude and longitude are required"}, 400

            lat = data.get("lat")
            lng = data.get("lng")

            if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
                return {"success": False, "error": "Invalid coordinates format"}, 400

            result = reverse_geocode_coordinates(lat, lng)
            if result["success"]:
                result["coordinates"] = {"lat": lat, "lng": lng}
            return result, 200
        except Exception as e:
            current_app.logger.exception(f"Error in reverse-geocode endpoint: {str(e)}")
            return {"success": False, "error": f"Server error: {str(e)}"}, 500

    def get(self):
        """GET method for reverse geocoding"""
        try:
            try:
                lat = float(request.args.get("lat", 0))
                lng = float(request.args.get("lng", 0))
            except (ValueError, TypeError):
                return {"success": False, "error": "Invalid coordinates format"}, 400

            if not lat and not lng:  # Check if both are zero/empty
                return {"success": False, "error": "Latitude and longitude are required"}, 400

            result = reverse_geocode_coordinates(lat, lng)
            if result["success"]:
                result["coordinates"] = {"lat": lat, "lng": lng}
            return result, 200
        except Exception as e:
            current_app.logger.exception(f"Error in reverse-geocode GET endpoint: {str(e)}")
            return {"success": False, "error": f"Server error: {str(e)}"}, 500

    def options(self):
        """Handle OPTIONS requests for the geocoding endpoint."""
        response = current_app.make_default_options_response()

        # Get origin from request headers
        origin = request.headers.get("Origin")
        allowed_origins = current_app.config.get("CORS_ORIGINS", [])

        # Add CORS headers if origin is allowed
        if origin and (origin in allowed_origins or "*" in allowed_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"  # Add GET to allowed methods
            response.headers[
                "Access-Control-Allow-Headers"
            ] = "Content-Type, Authorization, Accept, X-Requested-With, Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"

        return response


@api.route("/validate")
class AddressValidationResource(Resource):
    @api.doc("validate_address")
    @api.expect(geocoding_request)
    @api.marshal_with(validation_response)
    @api.response(200, "Address validation result")
    @api.response(400, "Invalid request")
    def post(self):
        """Validate if an address appears to be complete"""
        data = request.get_json()

        if not data or "address" not in data:
            return {"valid": False, "message": "Address not provided"}, 400

        address = data["address"]
        result = validate_address(address)

        return result, 200

    def options(self):
        """Handle OPTIONS requests for the address validation endpoint."""
        response = current_app.make_default_options_response()

        # Get origin from request headers
        origin = request.headers.get("Origin")
        allowed_origins = current_app.config.get("CORS_ORIGINS", [])

        # Add CORS headers if origin is allowed
        if origin and (origin in allowed_origins or "*" in allowed_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
            response.headers[
                "Access-Control-Allow-Headers"
            ] = "Content-Type, Authorization, Accept, X-Requested-With, Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"

        return response
