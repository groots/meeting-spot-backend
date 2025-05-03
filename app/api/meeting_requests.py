"""Meeting requests related endpoints."""

import uuid
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from .. import db
from ..models.meeting_request import MeetingRequest, MeetingRequestStatus
from ..models.user import User

# Create blueprint
meeting_requests_bp = Blueprint("meeting_requests", __name__)


@meeting_requests_bp.route("", methods=["POST"])
@jwt_required(optional=True)
def create_meeting_request():
    """Create a new meeting request."""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No input data provided"}), 400

    # Get user ID if authenticated
    current_user_id = get_jwt_identity()
    user = None

    if current_user_id:
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({"error": "Authenticated user not found"}), 404

    # Validate required fields
    required_fields = ["location_a", "user_b_email", "location_type"]
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    try:
        # Create new meeting request
        meeting_request = MeetingRequest(
            request_id=uuid.uuid4(),
            user_a_id=current_user_id,
            user_b_email=data["user_b_email"],
            user_b_name=data.get("user_b_name", ""),
            location_type=data["location_type"],
            location_a=data["location_a"],
            address_a_lat=data["location_a"].get("latitude", 0),
            address_a_lon=data["location_a"].get("longitude", 0),
            token_b=str(uuid.uuid4().hex),
            status=MeetingRequestStatus.PENDING_B_ADDRESS,
            session_identifier_a=data.get("session_identifier") if not current_user_id else None,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

        db.session.add(meeting_request)
        db.session.commit()

        return (
            jsonify({"message": "Meeting request created successfully", "meeting_request": meeting_request.to_dict()}),
            201,
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating meeting request: {str(e)}")
        return jsonify({"error": "Error creating meeting request"}), 500


@meeting_requests_bp.route("", methods=["GET"])
@jwt_required()
def get_meeting_requests():
    """Get all meeting requests for the current user."""
    current_user_id = get_jwt_identity()

    # Get user
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Get all meeting requests initiated by the user
    meeting_requests = MeetingRequest.query.filter_by(user_a_id=current_user_id).all()

    return jsonify({"meeting_requests": [req.to_dict() for req in meeting_requests]}), 200


@meeting_requests_bp.route("/<uuid:request_id>", methods=["GET"])
@jwt_required(optional=True)
def get_meeting_request(request_id):
    """Get a specific meeting request."""
    current_user_id = get_jwt_identity()

    # Get meeting request
    meeting_request = MeetingRequest.query.get(request_id)

    if not meeting_request:
        return jsonify({"error": "Meeting request not found"}), 404

    # Check if the user is authorized to view this meeting request
    if current_user_id and str(meeting_request.user_a_id) != current_user_id:
        return jsonify({"error": "Unauthorized to view this meeting request"}), 403

    return jsonify(meeting_request.to_dict()), 200


# Register the blueprint with the api
from . import api

api.register_blueprint(meeting_requests_bp, url_prefix="/meeting-requests")
