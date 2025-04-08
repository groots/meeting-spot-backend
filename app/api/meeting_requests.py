import uuid
from datetime import datetime, timedelta, timezone

from flask import request
from flask_restx import Namespace, Resource, fields

from .. import db
from ..models import ContactType, MeetingRequest, MeetingRequestStatus

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


@api.route("/")
class MeetingRequestList(Resource):
    @api.doc("create_request")
    @api.expect(create_request_model)
    @api.response(201, "Request created successfully")
    @api.response(400, "Invalid input")
    def post(self) -> None:
        """Create a new meeting request"""
        data = request.get_json()

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

        response_data = new_request.to_dict()
        # Add request_id to the response for backward compatibility
        response_data["request_id"] = str(new_request.request_id)
        return response_data, 201


@api.route("/<string:request_id>")
@api.param("request_id", "The request identifier")
class MeetingRequestResource(Resource):
    @api.doc("get_request")
    @api.response(200, "Request found")
    @api.response(404, "Request not found")
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


@api.route("/<string:request_id>/status")
@api.param("request_id", "The request identifier")
class MeetingRequestStatusResource(Resource):
    @api.doc("get_request_status")
    @api.response(200, "Status retrieved successfully")
    @api.response(404, "Request not found")
    def get(self, request_id) -> None:
        """Get the status of a meeting request"""
        try:
            request_id = uuid.UUID(request_id)
        except ValueError:
            return {"error": "Invalid request ID format"}, 400

        meeting_request = MeetingRequest.query.get(request_id)
        if not meeting_request:
            return {"error": "Request not found"}, 404

        return {
            "request_id": str(request_id),
            "status": meeting_request.status.value,
            "created_at": meeting_request.created_at.isoformat(),
            "expires_at": meeting_request.expires_at.isoformat(),
        }


@api.route("/<string:request_id>/respond")
@api.route("/<string:request_id>/respond/")
class MeetingRequestRespond(Resource):
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
@api.route("/<string:request_id>/results/")
class MeetingRequestResults(Resource):
    @api.doc("get_request_results")
    @api.response(200, "Results retrieved successfully")
    @api.response(404, "Request not found")
    def get(self, request_id) -> None:
        """Get the results of a meeting request"""
        try:
            request_id = uuid.UUID(request_id)
        except ValueError:
            return {"error": "Invalid request ID format"}, 400

        meeting_request = MeetingRequest.query.get(request_id)
        if not meeting_request:
            return {"error": "Request not found"}, 404

        return {
            "request_id": str(request_id),
            "status": meeting_request.status.value,
            "suggested_options": meeting_request.suggested_options,
            "selected_place": meeting_request.selected_place_details,
        }
