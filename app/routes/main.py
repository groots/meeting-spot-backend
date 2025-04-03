"""Main API routes for the application."""

import os
import re
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import googlemaps
from flask import Blueprint, current_app, jsonify, request, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.models import ContactType, MeetingRequest, MeetingRequestStatus, db
from flask_login import login_required, current_user
from app.models.meeting_request import MeetingRequest
from app.models.user import User

# Create a Blueprint for the main API functionality
# We'll add routes to this blueprint
api_bp = Blueprint("api", __name__, static_folder="../static", static_url_path="")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])


def validate_email(email) -> None:
    """Validate email format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_phone(phone) -> None:
    """Validate phone number format."""
    pattern = r"^\+?1?\d{9,15}$"
    return bool(re.match(pattern, phone))


def validate_contact_info(contact_type, contact) -> None:
    """Validate contact information based on type."""
    if contact_type == ContactType.EMAIL.value:
        if not validate_email(contact):
            return False, "Invalid email format"
    elif contact_type == ContactType.PHONE.value:
        if not validate_phone(contact):
            return False, "Invalid phone number format"
    return True, None


@api_bp.route("/")
def index():
    """Serve the index.html file."""
    return send_from_directory(api_bp.static_folder, "index.html")


@api_bp.route("/_next/<path:path>")
def next_static(path):
    """Serve Next.js static files."""
    return send_from_directory(os.path.join(api_bp.static_folder, "_next"), path)


@api_bp.route("/hello")
def hello() -> None:
    return jsonify(message="Hello from the API!")


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


# Test endpoint to verify encryption/decryption
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


@api_bp.route("/requests/<uuid:request_id>/select-spot", methods=["POST"])
@limiter.limit("30 per minute")
def select_meeting_spot(request_id) -> None:
    """Select a meeting spot for the request."""
    data = request.get_json()

    if not data or "place_id" not in data:
        return jsonify({"error": "Bad Request", "message": "No place_id provided"}), 400

    meeting_request = db.session.query(MeetingRequest).filter_by(request_id=request_id).first()

    if not meeting_request:
        return jsonify({"error": "Not Found", "message": "Meeting request not found"}), 404

    if meeting_request.status != MeetingRequestStatus.COMPLETED:
        return jsonify(
            {
                "error": "Bad Request",
                "message": "Cannot select spot until results are ready",
            }
        ), 400

    try:
        # Get place details from Google Places API
        gmaps = googlemaps.Client(key=current_app.config.get("GOOGLE_MAPS_API_KEY"))
        place_details = gmaps.place(
            data["place_id"],
            fields=[
                "name",
                "formatted_address",
                "formatted_phone_number",
                "website",
                "opening_hours",
                "rating",
                "user_ratings_total",
                "photos",
            ],
        )["result"]

        # Store selected place details
        meeting_request.selected_place_google_id = data["place_id"]
        meeting_request.selected_place_details = {
            "name": place_details["name"],
            "address": place_details["formatted_address"],
            "phone": place_details.get("formatted_phone_number"),
            "website": place_details.get("website"),
            "opening_hours": place_details.get("opening_hours", {}).get("weekday_text"),
            "rating": place_details.get("rating"),
            "total_ratings": place_details.get("user_ratings_total"),
            # Store first 3 photos
            "photos": place_details.get("photos", [])[:3],
        }

        db.session.commit()

        return jsonify(
            {
                "request_id": str(meeting_request.request_id),
                "status": "spot_selected",
                "selected_spot": meeting_request.selected_place_details,
            }
        ), 200

    except Exception as e:
        current_app.logger.error(f"Error selecting meeting spot: {e}")
        db.session.rollback()
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500


# Add other routes for authentication, user profiles etc. later

@api_bp.route("/meeting-requests", methods=["POST"])
@login_required
def create_meeting_request():
    """Create a new meeting request."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Validate required fields
    required_fields = ["title", "description", "location", "date", "time"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Create meeting request
    meeting_request = MeetingRequest(
        title=data["title"],
        description=data["description"],
        location=data["location"],
        date=data["date"],
        time=data["time"],
        user_id=current_user.id
    )

    db.session.add(meeting_request)
    db.session.commit()

    return jsonify(meeting_request.to_dict()), 201

@api_bp.route("/meeting-requests", methods=["GET"])
@login_required
def get_meeting_requests():
    """Get all meeting requests."""
    meeting_requests = MeetingRequest.query.all()
    return jsonify([request.to_dict() for request in meeting_requests])

@api_bp.route("/meeting-requests/<int:request_id>", methods=["GET"])
@login_required
def get_meeting_request(request_id):
    """Get a specific meeting request."""
    meeting_request = MeetingRequest.query.get_or_404(request_id)
    return jsonify(meeting_request.to_dict())

@api_bp.route("/meeting-requests/<int:request_id>", methods=["PUT"])
@login_required
def update_meeting_request(request_id):
    """Update a meeting request."""
    meeting_request = MeetingRequest.query.get_or_404(request_id)
    if meeting_request.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Update fields
    for field in ["title", "description", "location", "date", "time"]:
        if field in data:
            setattr(meeting_request, field, data[field])

    db.session.commit()
    return jsonify(meeting_request.to_dict())

@api_bp.route("/meeting-requests/<int:request_id>", methods=["DELETE"])
@login_required
def delete_meeting_request(request_id):
    """Delete a meeting request."""
    meeting_request = MeetingRequest.query.get_or_404(request_id)
    if meeting_request.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    db.session.delete(meeting_request)
    db.session.commit()
    return "", 204

@api_bp.route("/meeting-spots", methods=["POST"])
@login_required
def create_meeting_spot():
    """Create a new meeting spot."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Validate required fields
    required_fields = ["name", "address", "latitude", "longitude"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Create meeting spot
    meeting_spot = MeetingSpot(
        name=data["name"],
        address=data["address"],
        latitude=data["latitude"],
        longitude=data["longitude"]
    )

    db.session.add(meeting_spot)
    db.session.commit()

    return jsonify(meeting_spot.to_dict()), 201

@api_bp.route("/meeting-spots", methods=["GET"])
@login_required
def get_meeting_spots():
    """Get all meeting spots."""
    meeting_spots = MeetingSpot.query.all()
    return jsonify([spot.to_dict() for spot in meeting_spots])

@api_bp.route("/meeting-spots/<int:spot_id>", methods=["GET"])
@login_required
def get_meeting_spot(spot_id):
    """Get a specific meeting spot."""
    meeting_spot = MeetingSpot.query.get_or_404(spot_id)
    return jsonify(meeting_spot.to_dict())

@api_bp.route("/meeting-spots/<int:spot_id>", methods=["PUT"])
@login_required
def update_meeting_spot(spot_id):
    """Update a meeting spot."""
    meeting_spot = MeetingSpot.query.get_or_404(spot_id)
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Update fields
    for field in ["name", "address", "latitude", "longitude"]:
        if field in data:
            setattr(meeting_spot, field, data[field])

    db.session.commit()
    return jsonify(meeting_spot.to_dict())

@api_bp.route("/meeting-spots/<int:spot_id>", methods=["DELETE"])
@login_required
def delete_meeting_spot(spot_id):
    """Delete a meeting spot."""
    meeting_spot = MeetingSpot.query.get_or_404(spot_id)
    db.session.delete(meeting_spot)
    db.session.commit()
    return "", 204

@api_bp.route("/meeting-requests/<int:request_id>/accept-or-decline", methods=["POST"])
@login_required
def accept_or_decline_request(request_id):
    """Accept or decline a meeting request."""
    meeting_request = MeetingRequest.query.get_or_404(request_id)
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "response" not in data:
        return jsonify({"error": "Missing response"}), 400

    if data["response"] not in ["accept", "decline"]:
        return jsonify({"error": "Invalid response"}), 400

    if data["response"] == "accept":
        meeting_request.accepted_by = current_user.id
        meeting_request.status = "accepted"
    else:
        meeting_request.status = "declined"

    db.session.commit()
    return jsonify(meeting_request.to_dict())
