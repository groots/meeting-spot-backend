import re
import secrets
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union
import os
import uuid

import googlemaps
from flask import Blueprint, current_app, jsonify, request, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.models import ContactType, MeetingRequest, MeetingRequestStatus, db

# Import Config if needed directly, or rely on current_app.config
from app.utils.notifications import send_email, send_sms

# Create a Blueprint for the main API functionality
# We'll add routes to this blueprint
api_bp = Blueprint("api", __name__, static_folder="../static", static_url_path="")

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[
        "200 per day",
        "50 per hour"])


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

    required_fields = ["address_a_lat", "address_a_lon", "location_type", "user_b_contact_type", "user_b_contact"]
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
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        db.session.add(meeting_request)
        db.session.commit()

        return jsonify({
            "request_id": str(meeting_request.request_id),
            "token": meeting_request.token_b,
        }), 201

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

    return jsonify({
        "status": meeting_request.status.value,
        "expires_at": meeting_request.expires_at.isoformat(),
    }), 200


@api_bp.route("/meeting-requests/<request_id>/respond", methods=["POST"])
def respond_to_request(request_id) -> None:
    """Respond to a meeting request with address B."""
    try:
        request_id = uuid.UUID(request_id)
    except ValueError:
        return jsonify({"error": "Invalid request ID format"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["address_b", "token"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    meeting_request = MeetingRequest.query.get(request_id)
    if not meeting_request:
        return jsonify({"error": "Request not found"}), 404

    if meeting_request.token_b != data["token"]:
        return jsonify({"error": "Invalid token"}), 403

    if meeting_request.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return jsonify({"error": "Request has expired"}), 400

    try:
        meeting_request.address_b = data["address_b"]
        meeting_request.status = MeetingRequestStatus.CALCULATING
        db.session.commit()

        return jsonify({
            "status": meeting_request.status.value,
        }), 200

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
        return jsonify({
            "status": meeting_request.status.value,
        }), 200

    return jsonify({
        "status": meeting_request.status.value,
        "meeting_spots": meeting_request.meeting_spots,
    }), 200


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
    """
    Select a meeting spot for the request.
    """
    data = request.get_json()

    if not data or "place_id" not in data:
        return jsonify(
            {"error": "Bad Request", "message": "No place_id provided"}), 400

    meeting_request = db.session.query(
        MeetingRequest).filter_by(request_id=request_id).first()

    if not meeting_request:
        return (
            jsonify({"error": "Not Found",
                     "message": "Meeting request not found"}),
            404,
        )

    if meeting_request.status != MeetingRequestStatus.COMPLETED:
        return (
            jsonify(
                {
                    "error": "Bad Request",
                    "message": "Cannot select spot until results are ready",
                }
            ),
            400,
        )

    try:
        # Get place details from Google Places API
        gmaps = googlemaps.Client(
            key=current_app.config.get("GOOGLE_MAPS_API_KEY"))
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

        return (
            jsonify(
                {
                    "request_id": str(meeting_request.request_id),
                    "status": "spot_selected",
                    "selected_spot": meeting_request.selected_place_details,
                }
            ),
            200,
        )

    except Exception as e:
        current_app.logger.error(f"Error selecting meeting spot: {e}")
        db.session.rollback()
        return jsonify(
            {"error": "Internal Server Error", "message": str(e)}), 500


# Add other routes for authentication, user profiles etc. later
