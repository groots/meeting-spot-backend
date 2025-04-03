import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.fernet import Fernet
from flask import Blueprint, current_app, jsonify, request

from . import db
from .models import ContactType, MeetingRequest, MeetingRequestStatus

api_bp = Blueprint("api", __name__)


def get_encryption_key() -> None:
    """Get the encryption key from environment variables or app config."""
    key = current_app.config.get("ENCRYPTION_KEY")
    if key:
        return key if isinstance(key, bytes) else key.encode()

    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise ValueError("ENCRYPTION_KEY not found in config or environment")
    return key.encode()


def get_jwt_secret() -> None:
    """Get the JWT secret from environment variables."""
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret:
        raise ValueError("JWT_SECRET_KEY environment variable is not set")
    return secret


def encrypt_sensitive_data(data) -> None:
    """Encrypt sensitive data before storing."""
    fernet = Fernet(get_encryption_key())
    return fernet.encrypt(data.encode()).decode()


def decrypt_sensitive_data(encrypted_data) -> None:
    """Decrypt sensitive data after retrieving."""
    fernet = Fernet(get_encryption_key())
    return fernet.decrypt(encrypted_data.encode()).decode()


def generate_user_b_token(request_id) -> None:
    """Generate a secure token for user B to access the request."""
    payload = {
        "request_id": str(request_id),
        "exp": int(time.time()) + (24 * 60 * 60),  # 24 hours expiration
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm="HS256")


def verify_user_b_token(token) -> None:
    """Verify the token and return the request_id if valid."""
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=["HS256"])
        return payload["request_id"]
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


@api_bp.route("/meeting-requests/", methods=["POST"])
def create_request() -> None:
    """Create a new meeting request."""
    data = request.get_json()

    # Validate required fields
    required_fields = [
        "address_a",
        "location_type",
        "user_b_contact_type",
        "user_b_contact",
    ]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

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
        user_b_contact_encrypted=encrypt_sensitive_data(data["user_b_contact"]),  # Encrypt directly
        token_b=uuid.uuid4().hex,  # Generate a secure token
        status=MeetingRequestStatus.PENDING_B_ADDRESS,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    db.session.add(new_request)
    db.session.commit()

    # Generate token for user B
    user_b_token = generate_user_b_token(new_request.request_id)

    return jsonify(
        {
            "request_id": str(new_request.request_id),
            "user_b_token": user_b_token,
            "status": new_request.status.value,
        }
    )


@api_bp.route("/meeting-requests/<request_id>/status/", methods=["GET"])
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
    if meeting_request.expires_at < datetime.utcnow():
        meeting_request.status = MeetingRequestStatus.EXPIRED
        db.session.commit()
        return jsonify({"error": "Request has expired"}), 410

    # Generate token for user B if not provided
    user_b_token = generate_user_b_token(request_id)

    return jsonify(
        {
            "request_id": str(request_id),
            "status": meeting_request.status.value,
            "user_b_token": user_b_token,
            "created_at": meeting_request.created_at.isoformat(),
            "expires_at": meeting_request.expires_at.isoformat(),
        }
    )


@api_bp.route("/meeting-requests/<request_id>/respond/", methods=["POST"])
def respond_to_request(request_id) -> None:
    """Handle user B's response to a meeting request."""
    try:
        request_id = uuid.UUID(request_id)
    except ValueError:
        return jsonify({"error": "Invalid request ID format"}), 400

    meeting_request = MeetingRequest.query.get(request_id)
    if not meeting_request:
        return jsonify({"error": "Request not found"}), 404

    if meeting_request.status != MeetingRequestStatus.PENDING_B_ADDRESS:
        return jsonify({"error": "Request is not in the correct state"}), 400

    data = request.get_json()
    if "address_b" not in data:
        return jsonify({"error": "Missing address_b field"}), 400

    # Update request with user B's address
    meeting_request.address_b = data["address_b"]
    meeting_request.status = MeetingRequestStatus.CALCULATING
    db.session.commit()

    # TODO: Trigger the calculation process
    # This would typically involve creating a Cloud Task or using another
    # async processing method

    return jsonify({"request_id": str(request_id), "status": meeting_request.status.value})


@api_bp.route("/meeting-requests/<request_id>/results/", methods=["GET"])
def get_request_results(request_id) -> None:
    """Get the results of a meeting request calculation."""
    try:
        request_id = uuid.UUID(request_id)
    except ValueError:
        return jsonify({"error": "Invalid request ID format"}), 400

    meeting_request = MeetingRequest.query.get(request_id)
    if not meeting_request:
        return jsonify({"error": "Request not found"}), 404

    if meeting_request.status == MeetingRequestStatus.PENDING_B_ADDRESS:
        return jsonify({"error": "Waiting for user B to respond"}), 400

    if meeting_request.status == MeetingRequestStatus.CALCULATING:
        return jsonify({"request_id": str(request_id), "status": meeting_request.status.value})

    if meeting_request.status == MeetingRequestStatus.COMPLETED:
        return jsonify(
            {
                "request_id": str(request_id),
                "status": meeting_request.status.value,
                "results": {"meeting_spots": meeting_request.meeting_spots},
            }
        )

    return jsonify(
        {
            "request_id": str(request_id),
            "status": meeting_request.status.value,
            "error": "Calculation failed or request expired",
        }
    )


@api_bp.route("/meeting-requests/<request_id>/select-spot/", methods=["POST"])
def select_spot(request_id) -> None:
    """Handle selection of a meeting spot."""
    try:
        request_id = uuid.UUID(request_id)
    except ValueError:
        return jsonify({"error": "Invalid request ID format"}), 400

    meeting_request = MeetingRequest.query.get(request_id)
    if not meeting_request:
        return jsonify({"error": "Request not found"}), 404

    if meeting_request.status != MeetingRequestStatus.COMPLETED:
        return jsonify({"error": "Request is not in the correct state"}), 400

    data = request.get_json()
    if "place_id" not in data:
        return jsonify({"error": "Missing place_id field"}), 400

    # TODO: Update the selected spot in the database
    # For now, return a mock response
    return jsonify(
        {
            "request_id": str(request_id),
            "selected_spot": {
                "name": "Selected Meeting Spot",
                "address": "123 Main St",
                "place_id": data["place_id"],
            },
        }
    )


@api_bp.route("/monitoring/metrics")
def metrics() -> None:
    """Endpoint for monitoring metrics."""
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})


@api_bp.route("/health")
def health_check() -> None:
    """Health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})
