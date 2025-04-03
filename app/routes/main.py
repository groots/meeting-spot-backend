"""Main API routes for the application."""

import os
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple

from flask import Blueprint, current_app, jsonify, request, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.models import ContactType, MeetingRequest, MeetingRequestStatus, db


# Create a Blueprint for the v2 API functionality
api_bp = Blueprint("api_v2", __name__, static_folder="../static", static_url_path="")


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])


def validate_request_id(request_id: str) -> Tuple[bool, str, int]:
    """Validate the request ID format."""
    try:
        return True, str(uuid.UUID(request_id)), 200
    except ValueError:
        return False, "Invalid request ID format", 400


def validate_request_data(data: Dict[str, Any]) -> Tuple[bool, str, int]:
    """Validate the request data."""
    if not data:
        return False, "No data provided", 400

    required_fields = ["address_b", "token"]
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}", 400

    return True, "", 200


def validate_meeting_request(meeting_request: Optional[MeetingRequest], token: str) -> Tuple[bool, str, int]:
    """Validate the meeting request and token."""
    if not meeting_request:
        return False, "Request not found", 404

    if meeting_request.token_b != token:
        return False, "Invalid token", 403

    if meeting_request.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return False, "Request has expired", 400

    return True, "", 200


@api_bp.route("/")
def index():
    """Serve the index.html file."""
    return send_from_directory(api_bp.static_folder, "index.html")


@api_bp.route("/_next/<path:path>")
def next_static(path):
    """Serve Next.js static files."""
    return send_from_directory(os.path.join(api_bp.static_folder, "_next"), path)


@api_bp.route("/health", methods=["GET"])
def health_check() -> None:
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


@api_bp.route("/meeting-requests/", methods=["POST"])
def create_request() -> None:
    """Create a new meeting request."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = [
        "address_a_lat",
        "address_a_lon",
        "location_type",
        "user_b_contact_type",
        "user_b_contact",
    ]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    try:
        meeting_request = MeetingRequest(
            address_a_lat=data["address_a_lat"],
            address_a_lon=data["address_a_lon"],
            location_type=data["location_type"],
            user_b_contact_type=ContactType(data["user_b_contact_type"]),
            user_b_contact=data["user_b_contact"],
            token_b=secrets.token_urlsafe(32),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.session.add(meeting_request)
        db.session.commit()

        return jsonify(
            {
                "request_id": str(meeting_request.request_id),
                "token": meeting_request.token_b,
            }
        ), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


@api_bp.route("/meeting-requests/<request_id>/status", methods=["GET"])
def get_request_status(request_id) -> None:
    """Get the status of a meeting request."""
    try:
        request_id = uuid.UUID(request_id)
    except ValueError:
        return jsonify({"error": "Invalid request ID format"}), 400

    meeting_request = MeetingRequest.query.get(request_id)
    if not meeting_request:
        return jsonify({"error": "Request not found"}), 404

    # Check if request has expired
    if meeting_request.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return jsonify({"error": "Request has expired"}), 400

    return jsonify(
        {
            "status": meeting_request.status.value,
            "expires_at": meeting_request.expires_at.isoformat(),
        }
    ), 200


@api_bp.route("/meeting-requests/<request_id>/respond", methods=["POST"])
def respond_to_request(request_id) -> None:
    """Respond to a meeting request with address B."""
    # Validate request ID
    is_valid, result, status_code = validate_request_id(request_id)
    if not is_valid:
        return jsonify({"error": result}), status_code

    # Validate request data
    data = request.get_json()
    is_valid, error_msg, status_code = validate_request_data(data)
    if not is_valid:
        return jsonify({"error": error_msg}), status_code

    # Get and validate meeting request
    meeting_request = MeetingRequest.query.get(result)
    is_valid, error_msg, status_code = validate_meeting_request(meeting_request, data["token"])
    if not is_valid:
        return jsonify({"error": error_msg}), status_code

    try:
        meeting_request.address_b = data["address_b"]
        meeting_request.status = MeetingRequestStatus.CALCULATING
        db.session.commit()

        return jsonify({"status": meeting_request.status.value}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


@api_bp.route("/meeting-requests/<request_id>/results", methods=["GET"])
def get_request_results(request_id) -> None:
    """Get the results of a meeting request."""
    try:
        request_id = uuid.UUID(request_id)
    except ValueError:
        return jsonify({"error": "Invalid request ID format"}), 400

    meeting_request = MeetingRequest.query.get(request_id)
    if not meeting_request:
        return jsonify({"error": "Request not found"}), 404

    if meeting_request.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return jsonify({"error": "Request has expired"}), 400

    if meeting_request.status != MeetingRequestStatus.COMPLETED:
        return jsonify({"status": meeting_request.status.value}), 200

    return jsonify(
        {
            "status": meeting_request.status.value,
            "meeting_spots": meeting_request.meeting_spots,
        }
    ), 200


@api_bp.route("/requests/<uuid:request_id>/contact", methods=["GET"])
@limiter.limit("30 per minute")  # Rate limit for contact info retrieval
def get_contact_info(request_id) -> None:
    """Test endpoint to verify encryption/decryption is working."""
    meeting_request = MeetingRequest.query.get_or_404(request_id)
    return jsonify(
        {
            "contact_type": meeting_request.user_b_contact_type.value,
            "contact_encrypted": meeting_request.user_b_contact_encrypted,
            "contact_decrypted": meeting_request.user_b_contact,
        }
    )
