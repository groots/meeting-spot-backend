from flask import current_app, request
from flask_restx import Namespace, Resource, fields

from ..utils.geocoding import geocode_address, validate_address

# Create geocoding namespace
api = Namespace("geocoding", description="Geocoding operations")

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
        "address": fields.String(required=True, description="Address to geocode"),
    },
)


@api.route("")
class GeocodingResource(Resource):
    @api.doc("geocode_address")
    @api.expect(geocoding_request)
    @api.marshal_with(geocoding_response)
    @api.response(200, "Address geocoded successfully")
    @api.response(400, "Invalid request")
    @api.response(500, "Server error")
    def post(self):
        """Geocode an address to latitude and longitude coordinates"""
        try:
            data = request.get_json()
            current_app.logger.info(f"Geocoding request received: {data}")

            if not data:
                current_app.logger.error("No JSON data in request")
                return {"success": False, "error": "No data provided"}, 400

            if "address" not in data:
                current_app.logger.error("No address field in request data")
                return {"success": False, "error": "Address not provided"}, 400

            address = data["address"]
            current_app.logger.info(f"Processing geocoding request for address: {address}")

            # Handle special format of "Location (lat, lng)"
            import re

            location_pattern = re.compile(r"Location \((-?\d+\.\d+), (-?\d+\.\d+)\)")
            location_match = location_pattern.match(address) if address else None

            if location_match:
                # Extract coordinates directly from the string
                lat = float(location_match.group(1))
                lng = float(location_match.group(2))
                current_app.logger.info(f"Extracted coordinates from address string: ({lat}, {lng})")

                return {
                    "success": True,
                    "coordinates": {"lat": lat, "lng": lng},
                    "formatted_address": address,
                    "quality": "high",  # Direct coordinates are considered high quality
                }, 200

            # Normal geocoding
            result = geocode_address(address)
            current_app.logger.info(f"Geocoding result: {result}")

            if not result["success"]:
                # If geocoding failed, return a 400 status code
                return result, 400

            return result, 200

        except Exception as e:
            current_app.logger.exception(f"Error in geocoding endpoint: {str(e)}")
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
            response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
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
