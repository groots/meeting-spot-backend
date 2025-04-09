import uuid
from datetime import datetime, timedelta, timezone

from flask import current_app, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource, fields

from .. import db
from ..models import ContactType, MeetingRequest, MeetingRequestStatus, User
from ..utils.notifications import send_email

api = Namespace("meeting-requests", description="Meeting request operations")

# Swagger models
meeting_request_model = api.model(
    "MeetingRequest",
    {
        "request_id": fields.String(description="Unique identifier for the request"),
        "user_a_id": fields.String(description="ID of the user who initiated the request"),
        "user_b_contact_type": fields.String(description="Type of contact for user B (email, phone, sms)"),
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

        # TODO: Geocode address_a to get lat/lon
        # For now, using dummy coordinates
        address_a_lat = 37.7749
        address_a_lon = -122.4194

        # Create new request
        new_request = MeetingRequest(
            user_a_id=user.id,
            address_a_lat=address_a_lat,
            address_a_lon=address_a_lon,
            location_type=data["location_type"],
            user_b_contact_type=ContactType(data["user_b_contact_type"]),
            user_b_contact=data["user_b_contact"],
            token_b=uuid.uuid4().hex,
            status=MeetingRequestStatus.PENDING_B_ADDRESS,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )

        db.session.add(new_request)
        db.session.commit()

        # Send email to user B if contact type is email
        if new_request.user_b_contact_type == ContactType.EMAIL:
            base_url = current_app.config.get("FRONTEND_URL", "http://localhost:3000")
            response_url = f"{base_url}/request/{new_request.request_id}?token={new_request.token_b}"

            subject = "You've been invited to find a meeting spot!"
            body = f"""
Hello!

{user.email} has invited you to find a convenient meeting spot.

To respond with your location, please click the following link:
{response_url}

This link will expire in 24 hours.

Best regards,
Find a Meeting Spot Team
"""
            send_email(new_request.user_b_contact, subject, body)

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

        # TODO: Geocode address_b to get lat/lon
        # For now, using dummy coordinates
        address_b_lat = 37.7833
        address_b_lon = -122.4167

        meeting_request.address_b_lat = address_b_lat
        meeting_request.address_b_lon = address_b_lon
        meeting_request.status = MeetingRequestStatus.CALCULATING
        meeting_request.updated_at = datetime.now(timezone.utc)

        db.session.commit()

        return {"status": meeting_request.status.value}


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

        return {
            "request_id": str(request_id),
            "status": meeting_request.status.value,
            "suggested_options": meeting_request.suggested_options,
            "selected_place": meeting_request.selected_place_details,
        }
