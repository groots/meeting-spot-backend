import uuid
from datetime import datetime, timedelta, timezone

from flask import current_app, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource, fields

from .. import db
from ..models import Contact, ContactType, MeetingRequest, MeetingRequestStatus, User
from ..utils.geocoding import geocode_address
from ..utils.location import process_meeting_request
from ..utils.notifications import send_email
from ..utils.stripe_helpers import is_premium_feature

api = Namespace("meeting-requests", description="Meeting request operations")

# Swagger models
meeting_request_model = api.model(
    "MeetingRequest",
    {
        "request_id": fields.String(description="Unique identifier for the request"),
        "user_a_id": fields.String(description="ID of the user who initiated the request"),
        "user_b_contact_type": fields.String(description="Type of contact for user B (email, phone, sms)"),
        "user_b_contact": fields.String(description="Contact information of user B (email/phone/etc)"),
        "user_b_email": fields.String(description="Email address of user B (legacy field)"),
        "user_b_name": fields.String(description="Name of user B"),
        "location_type": fields.String(description="Type of location (e.g., Restaurant / Food)"),
        "address_a_lat": fields.Float(description="Latitude of user A's location"),
        "address_a_lon": fields.Float(description="Longitude of user A's location"),
        "address_b_lat": fields.Float(description="Latitude of user B's location"),
        "address_b_lon": fields.Float(description="Longitude of user B's location"),
        "status": fields.String(description="Current status of the request"),
        "created_at": fields.DateTime(description="When the request was created"),
        "updated_at": fields.DateTime(description="When the request was last updated"),
        "expires_at": fields.DateTime(description="When the request expires"),
    },
)

create_request_model = api.model(
    "CreateRequest",
    {
        "address_a": fields.String(required=True, description="Address of user A"),
        "location_type": fields.String(required=True, description="Type of location"),
        "user_b_contact_type": fields.String(required=True, description="Type of contact for user B"),
        "user_b_contact": fields.String(required=True, description="Contact information for user B"),
        "user_b_name": fields.String(description="Name of user B"),
        "save_as_contact": fields.Boolean(description="Whether to save user B as a contact"),
    },
)

update_request_model = api.model(
    "UpdateRequest",
    {
        "status": fields.String(description="New status of the request"),
        "meeting_location": fields.String(description="New meeting location details"),
    },
)


@api.route("/")
class MeetingRequestList(Resource):
    @api.doc("create_request")
    @api.expect(create_request_model)
    @api.response(201, "Request created successfully")
    @api.response(400, "Invalid input")
    @jwt_required()
    def post(self) -> None:
        """Create a new meeting request"""
        data = request.get_json()

        # Get user from JWT token
        user_id = get_jwt_identity()
        user = User.get_by_token_identity(user_id)
        if not user:
            return {"error": "User not found"}, 404

        # Validate required fields
        required_fields = [
            "address_a",
            "location_type",
            "user_b_contact_type",
            "user_b_contact",
        ]
        if not all(field in data for field in required_fields):
            return {"error": "Missing required fields"}, 400

        try:
            # Encrypt user_b_contact for storage
            user_b_contact = data["user_b_contact"]
            contact_type = ContactType(data["user_b_contact_type"].lower())

            # Get location data
            address_a = data["address_a"]
            if "address_a_lat" in data and "address_a_lon" in data:
                address_a_lat = float(data["address_a_lat"])
                address_a_lon = float(data["address_a_lon"])
            else:
                # If coordinates not provided, try to geocode the address
                current_app.logger.info(f"Geocoding address: {address_a}")
                result = geocode_address(address_a)

                if result["success"] and "coordinates" in result:
                    address_a_lat = result["coordinates"]["lat"]
                    address_a_lon = result["coordinates"]["lng"]
                    current_app.logger.info(f"Geocoded address to: ({address_a_lat}, {address_a_lon})")
                else:
                    # If geocoding fails, use default SF coordinates
                    current_app.logger.warning(
                        f"Geocoding failed, using default coordinates. Error: {result.get('error')}"
                    )
                    address_a_lat = 37.7749  # Default SF latitude
                    address_a_lon = -122.4194  # Default SF longitude

            location_a = {"address": address_a, "latitude": address_a_lat, "longitude": address_a_lon}

            # Create meeting request
            user_b_name = data.get("user_b_name", "")

            # Create a new meeting request - avoid setting user_b_name in constructor if database doesn't have the column
            new_request = MeetingRequest(
                user_a_id=user.id if user else None,
                address_a_lat=address_a_lat,
                address_a_lon=address_a_lon,
                location_a=location_a,
                location_type=data["location_type"],
                user_b_contact_type=contact_type,
                user_b_contact=user_b_contact,
                token_b=uuid.uuid4().hex,
                status=MeetingRequestStatus.PENDING_B_ADDRESS,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )

            # Set user_b_name after creation to use the hybrid property
            if user_b_name:
                new_request.user_b_name = user_b_name

            db.session.add(new_request)

            # If user wants to save as contact and is premium, create a contact
            save_as_contact = data.get("save_as_contact", False)
            if save_as_contact:
                # Check if contacts is a premium feature
                if is_premium_feature("contacts") and not user.is_premium():
                    return {
                        "error": "Premium subscription required",
                        "message": "Saving contacts requires a premium subscription",
                        "request_created": False,
                    }, 402

                # Check if contact with this email already exists
                if user_b_name:
                    existing_contact = Contact.query.filter_by(user_id=user.id, email=user_b_name).first()

                    if existing_contact:
                        # Update existing contact with new info if provided
                        if user_b_name and not existing_contact.name:
                            existing_contact.name = user_b_name
                            existing_contact.updated_at = datetime.now(timezone.utc)

                        # Associate the meeting request with the existing contact
                        new_request.contacts.append(existing_contact)
                    else:
                        # Create new contact
                        contact = Contact(
                            user_id=user.id,
                            name=user_b_name or "Unknown",
                            email=user_b_name,
                        )
                        db.session.add(contact)

                        # Associate the meeting request with the new contact
                        new_request.contacts.append(contact)

            db.session.commit()

        except (ValueError, TypeError) as e:
            current_app.logger.exception(f"Error processing coordinates: {str(e)}")
            return {"error": f"Invalid coordinate format: {str(e)}"}, 400

        # Send email to user B if contact type is email
        if new_request.user_b_contact_type == ContactType.EMAIL:
            base_url = current_app.config.get("FRONTEND_URL", "http://localhost:3000")
            response_url = f"{base_url}/request/{new_request.request_id}?token={new_request.token_b}"

            subject = "You've been invited to find a meeting spot!"
            body = f"""
Hello{f' {user_b_name}' if user_b_name else ''}!

{user.email} has invited you to find a convenient meeting spot.

To respond with your location, please click the following link:
{response_url}

This link will expire in 24 hours.

Best regards,
Find a Meeting Spot Team
"""
            send_email(user_b_name, subject, body)

        response_data = new_request.to_dict()
        # Add request_id to the response for backward compatibility
        response_data["request_id"] = str(new_request.request_id)
        return response_data, 201

    @api.doc("get_requests_list")
    @api.response(200, "List of requests")
    @jwt_required()
    def get(self) -> None:
        """Get a list of meeting requests for the current user"""
        user_id = get_jwt_identity()
        user = User.get_by_token_identity(user_id)
        if not user:
            return {"error": "User not found"}, 404

        meeting_requests = MeetingRequest.query.filter_by(user_a_id=user.id).all()
        return [request.to_dict() for request in meeting_requests]

    def options(self):
        """Handle OPTIONS requests for the meeting request list endpoint."""
        response = current_app.make_default_options_response()

        # Get origin from request headers
        origin = request.headers.get("Origin")
        allowed_origins = current_app.config.get("CORS_ORIGINS", [])

        # Add CORS headers if origin is allowed
        if origin and (origin in allowed_origins or "*" in allowed_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers[
                "Access-Control-Allow-Headers"
            ] = "Content-Type, Authorization, Accept, X-Requested-With, Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"

        return response


@api.route("/<string:request_id>")
@api.param("request_id", "The request identifier")
class MeetingRequestResource(Resource):
    @api.doc("get_request")
    @api.response(200, "Request found")
    @api.response(404, "Request not found")
    @jwt_required()
    def get(self, request_id) -> None:
        """Get a meeting request by ID"""
        try:
            request_id = uuid.UUID(request_id)
        except ValueError:
            return {"error": "Invalid request ID format"}, 400

        meeting_request = MeetingRequest.query.get(request_id)
        if not meeting_request:
            return {"error": "Request not found"}, 404

        return meeting_request.to_dict()

    @api.doc("update_request")
    @api.expect(update_request_model)
    @api.response(200, "Request updated successfully")
    @api.response(404, "Request not found")
    @jwt_required()
    def put(self, request_id):
        """Update a meeting request."""
        try:
            request_id_uuid = uuid.UUID(request_id)
            user_id = get_jwt_identity()
            user = User.get_by_token_identity(user_id)
            if not user:
                return {"message": "User not found"}, 404

            data = request.get_json()

            meeting_request = MeetingRequest.query.get(request_id_uuid)
            if not meeting_request:
                return {"message": "Meeting request not found"}, 404

            if meeting_request.user_a_id != user.id:
                return {"message": "Unauthorized"}, 403

            # Handle address_b coordinates
            if "address_b_lat" in data and "address_b_lon" in data:
                meeting_request.address_b_lat = data["address_b_lat"]
                meeting_request.address_b_lon = data["address_b_lon"]
                # When address_b is provided, automatically set status to CALCULATING
                meeting_request.status = MeetingRequestStatus.CALCULATING
            elif "status" in data:
                try:
                    meeting_request.status = MeetingRequestStatus(data["status"])
                except ValueError:
                    return {"message": "Invalid status value"}, 400

            if "meeting_location" in data:
                # TODO: Geocode meeting_location to get lat/lon
                meeting_request.selected_place_details = data["meeting_location"]

            meeting_request.updated_at = datetime.now(timezone.utc)
            db.session.commit()

            return meeting_request.to_dict()

        except ValueError:
            return {"message": "Invalid request ID format"}, 400

    @api.doc("delete_request")
    @api.response(204, "Request deleted successfully")
    @api.response(404, "Request not found")
    @jwt_required()
    def delete(self, request_id):
        """Delete a meeting request."""
        try:
            request_id_uuid = uuid.UUID(request_id)
            user_id = get_jwt_identity()
            user = User.get_by_token_identity(user_id)
            if not user:
                return {"message": "User not found"}, 404

            meeting_request = MeetingRequest.query.get(request_id_uuid)
            if not meeting_request:
                return {"message": "Meeting request not found"}, 404

            if meeting_request.user_a_id != user.id:
                return {"message": "Unauthorized"}, 403

            db.session.delete(meeting_request)
            db.session.commit()

            return "", 204

        except ValueError:
            return {"message": "Invalid request ID format"}, 400

    def options(self, request_id):
        """Handle OPTIONS requests for the meeting request resource endpoint."""
        response = current_app.make_default_options_response()

        # Get origin from request headers
        origin = request.headers.get("Origin")
        allowed_origins = current_app.config.get("CORS_ORIGINS", [])

        # Add CORS headers if origin is allowed
        if origin and (origin in allowed_origins or "*" in allowed_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, PUT, DELETE, OPTIONS"
            response.headers[
                "Access-Control-Allow-Headers"
            ] = "Content-Type, Authorization, Accept, X-Requested-With, Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"

        return response


@api.route("/<string:request_id>/status")
@api.param("request_id", "The request identifier")
class MeetingRequestStatusResource(Resource):
    @api.doc("get_request_status")
    @api.response(200, "Status retrieved successfully")
    @api.response(404, "Request not found")
    @jwt_required()
    def get(self, request_id) -> None:
        """Get the status of a meeting request"""
        try:
            request_id = uuid.UUID(request_id)
        except ValueError:
            return {"error": "Invalid request ID format"}, 400

        # Get user from JWT token
        user_id = get_jwt_identity()
        user = User.get_by_token_identity(user_id)
        if not user:
            return {"error": "User not found"}, 404

        meeting_request = MeetingRequest.query.get(request_id)
        if not meeting_request:
            return {"error": "Request not found"}, 404

        # Check if user owns the request
        if meeting_request.user_a_id != user.id:
            return {"error": "Unauthorized"}, 403

        return {
            "request_id": str(request_id),
            "status": meeting_request.status.value,
            "created_at": meeting_request.created_at.isoformat(),
            "expires_at": meeting_request.expires_at.isoformat(),
        }

    def options(self, request_id):
        """Handle OPTIONS requests for the meeting request status endpoint."""
        response = current_app.make_default_options_response()

        # Get origin from request headers
        origin = request.headers.get("Origin")
        allowed_origins = current_app.config.get("CORS_ORIGINS", [])

        # Add CORS headers if origin is allowed
        if origin and (origin in allowed_origins or "*" in allowed_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers[
                "Access-Control-Allow-Headers"
            ] = "Content-Type, Authorization, Accept, X-Requested-With, Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"

        return response


@api.route("/<string:request_id>/respond")
@api.param("request_id", "The request identifier")
class MeetingRequestResponseResource(Resource):
    @api.doc("respond_to_request")
    @api.response(200, "Response submitted successfully")
    @api.response(400, "Invalid input")
    @api.response(404, "Request not found")
    def post(self, request_id) -> None:
        """Submit a response to a meeting request"""
        try:
            request_id = uuid.UUID(request_id)
        except ValueError:
            return {"error": "Invalid request ID format"}, 400

        data = request.get_json()
        if not data or "address_b" not in data or "token" not in data:
            return {"error": "Missing required fields"}, 400

        meeting_request = MeetingRequest.query.get(request_id)
        if not meeting_request:
            return {"error": "Request not found"}, 404

        if meeting_request.token_b != data["token"]:
            return {"error": "Invalid token"}, 400

        # Extract coordinates from request data
        try:
            if "address_b_lat" in data and "address_b_lon" in data:
                address_b_lat = float(data["address_b_lat"])
                address_b_lon = float(data["address_b_lon"])
                # Validate coordinate ranges
                if not (-90 <= address_b_lat <= 90) or not (-180 <= address_b_lon <= 180):
                    return {
                        "error": "Invalid coordinates. Latitude must be between -90 and 90, longitude between -180 and 180"
                    }, 400
            else:
                # Default coordinates if geocoding isn't implemented yet
                current_app.logger.warning(f"Missing coordinates for request {request_id}, using defaults")
                address_b_lat = 37.7833
                address_b_lon = -122.4167

            # Log coordinates being used
            current_app.logger.info(f"User B coordinates for request {request_id}: ({address_b_lat}, {address_b_lon})")

            # Ensure address_a coordinates are valid
            if meeting_request.address_a_lat is None or meeting_request.address_a_lon is None:
                current_app.logger.error(f"Missing address_a coordinates for request {request_id}")
                meeting_request.status = MeetingRequestStatus.FAILED
                db.session.commit()
                return {"error": "Missing address_a coordinates"}, 400

            meeting_request.address_b_lat = address_b_lat
            meeting_request.address_b_lon = address_b_lon
            meeting_request.status = MeetingRequestStatus.CALCULATING
            meeting_request.updated_at = datetime.now(timezone.utc)

            # Save the coordinates first
            db.session.commit()

        except (ValueError, TypeError) as e:
            current_app.logger.exception(f"Error parsing coordinates for request {request_id}: {str(e)}")
            return {"error": f"Invalid coordinate format: {str(e)}"}, 400

        # Process the request to find meeting spots
        try:
            # Import here to avoid circular imports
            from ..utils.location import process_meeting_request

            # Calculate equidistant meeting spots
            success = process_meeting_request(meeting_request)

            if success:
                current_app.logger.info(f"Successfully processed meeting request {meeting_request.request_id}")
            else:
                current_app.logger.error(f"Failed to process meeting request {meeting_request.request_id}")

            # Save the updated meeting request with results
            db.session.commit()

            return {"status": meeting_request.status.value}
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(f"Error processing meeting request: {str(e)}")
            meeting_request.status = MeetingRequestStatus.FAILED
            db.session.commit()
            return {"error": "Failed to process meeting request", "status": "failed"}, 500

    def options(self, request_id):
        """Handle OPTIONS requests for the meeting request response endpoint."""
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


@api.route("/<string:request_id>/results")
@api.param("request_id", "The request identifier")
class MeetingRequestResultsResource(Resource):
    @api.doc("get_request_results")
    @api.response(200, "Results retrieved successfully")
    @api.response(404, "Request not found")
    @jwt_required()
    def get(self, request_id) -> None:
        """Get the results of a meeting request"""
        try:
            request_id = uuid.UUID(request_id)
        except ValueError:
            return {"error": "Invalid request ID format"}, 400

        # Get user from JWT token
        user_id = get_jwt_identity()
        user = User.get_by_token_identity(user_id)
        if not user:
            return {"error": "User not found"}, 404

        meeting_request = MeetingRequest.query.get(request_id)
        if not meeting_request:
            return {"error": "Request not found"}, 404

        # Check if user owns the request
        if meeting_request.user_a_id != user.id:
            return {"error": "Unauthorized"}, 403

        # If meeting request is still in CALCULATING status, try to process it
        if meeting_request.status == MeetingRequestStatus.CALCULATING:
            try:
                # Check if we have all required coordinates
                if (
                    meeting_request.address_a_lat is None
                    or meeting_request.address_a_lon is None
                    or meeting_request.address_b_lat is None
                    or meeting_request.address_b_lon is None
                ):
                    current_app.logger.error(f"Missing coordinates for meeting request {meeting_request.request_id}")
                    meeting_request.status = MeetingRequestStatus.FAILED
                    db.session.commit()
                    return {
                        "error": "Missing coordinates",
                        "status": meeting_request.status.value,
                        "request_id": str(request_id),
                    }, 400

                from ..utils.location import process_meeting_request

                current_app.logger.info(
                    f"Attempting to process meeting request {meeting_request.request_id} during results fetch"
                )
                process_success = process_meeting_request(meeting_request)
                if process_success:
                    db.session.commit()
                    current_app.logger.info(
                        f"Processed meeting request {meeting_request.request_id} during results fetch"
                    )
                else:
                    current_app.logger.warning(
                        f"Failed to process meeting request {meeting_request.request_id} during results fetch"
                    )
            except Exception as e:
                current_app.logger.exception(f"Error processing meeting request during results fetch: {str(e)}")

        # Calculate midpoint for frontend reference
        midpoint = None
        if (
            meeting_request.address_a_lat is not None
            and meeting_request.address_a_lon is not None
            and meeting_request.address_b_lat is not None
            and meeting_request.address_b_lon is not None
        ):
            try:
                from ..utils.location import calculate_midpoint

                mid_lat, mid_lon = calculate_midpoint(
                    meeting_request.address_a_lat,
                    meeting_request.address_a_lon,
                    meeting_request.address_b_lat,
                    meeting_request.address_b_lon,
                )
                midpoint = {"lat": mid_lat, "lng": mid_lon}
            except Exception as e:
                current_app.logger.exception(f"Error calculating midpoint: {str(e)}")
                midpoint = None

        # Prepare response locations data if both coordinates exist
        locations = None
        if meeting_request.address_a_lat is not None and meeting_request.address_a_lon is not None:
            locations = {"a": {"lat": meeting_request.address_a_lat, "lng": meeting_request.address_a_lon}}

            if meeting_request.address_b_lat is not None and meeting_request.address_b_lon is not None:
                locations["b"] = {"lat": meeting_request.address_b_lat, "lng": meeting_request.address_b_lon}

        return {
            "request_id": str(request_id),
            "status": meeting_request.status.value,
            "suggested_options": meeting_request.suggested_options or [],
            "selected_place": meeting_request.selected_place_details,
            "midpoint": midpoint,
            "locations": locations,
        }

    def options(self, request_id):
        """Handle OPTIONS requests for the meeting request results endpoint."""
        response = current_app.make_default_options_response()

        # Get origin from request headers
        origin = request.headers.get("Origin")
        allowed_origins = current_app.config.get("CORS_ORIGINS", [])

        # Add CORS headers if origin is allowed
        if origin and (origin in allowed_origins or "*" in allowed_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers[
                "Access-Control-Allow-Headers"
            ] = "Content-Type, Authorization, Accept, X-Requested-With, Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"

        return response
