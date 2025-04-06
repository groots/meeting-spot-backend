"""API blueprints for the application."""

import uuid
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_restx import Api

from .. import db
from ..models import ContactType, MeetingRequest, MeetingRequestStatus
from .auth import api as auth_ns
from .meeting_requests import api as meeting_requests_ns
from .users import api as users_ns

# Create API v1 blueprint
api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# Create API v2 blueprint
api_v2_bp = Blueprint("api_v2", __name__, url_prefix="/api/v2")

# Create a limiter instance
limiter = Limiter(key_func=get_remote_address)

# Add a test route directly to the blueprint
@api_v1_bp.route("/test/")
def test_route():
    return jsonify({"message": "API v1 test route working"})


# Add a meeting requests route directly to the blueprint
@api_v1_bp.route("/meeting-requests/", methods=["POST"])
@limiter.limit("100 per hour")
def create_meeting_request():
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


# Add a status route directly to the blueprint with a more lenient rate limit
@api_v1_bp.route("/meeting-requests/<string:request_id>/status/", methods=["GET"])
@limiter.limit("300 per hour")  # More lenient rate limit for status endpoint
def get_meeting_request_status(request_id):
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


# Create API v1 instance
api_v1 = Api(
    api_v1_bp,
    version="1.0",
    title="Find a Meeting Spot API v1",
    description="API v1 for finding meeting spots between two locations",
    doc="/docs",  # Always enable Swagger UI
    serve_challenge_on_401=True,
    default_mediatype="application/json",
    catch_all_404s=True,
)

# Create API v2 instance
api_v2 = Api(
    api_v2_bp,
    version="2.0",
    title="Find a Meeting Spot API v2",
    description="API v2 for finding meeting spots between two locations",
    doc="/docs",  # Always enable Swagger UI
    serve_challenge_on_401=True,
    default_mediatype="application/json",
    catch_all_404s=True,
)

# Register namespaces for v1
api_v1.add_namespace(auth_ns, path="/auth")
api_v1.add_namespace(meeting_requests_ns, path="/meeting-requests")
api_v1.add_namespace(users_ns, path="/users")

# Register namespaces for v2
api_v2.add_namespace(auth_ns, path="/auth")
api_v2.add_namespace(meeting_requests_ns, path="/meeting-requests")
api_v2.add_namespace(users_ns, path="/users")

# No need to import routes since we're using Flask-RESTX namespaces
