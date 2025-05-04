"""Meeting Requests API Blueprint.

This module provides the API endpoints for meeting requests.
"""

import uuid
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.models import ContactType, MeetingRequest, MeetingRequestStatus, User, db
from app.utils.location import process_meeting_request
from app.utils.notifications import send_email

# Create blueprint
meeting_requests_bp = Blueprint("meeting_requests", __name__)


@meeting_requests_bp.route("", methods=["POST"])
@jwt_required()
def create_meeting_request():
    """Create a new meeting request."""
    data = request.get_json()

    # Get user from JWT token
    user_id = get_jwt_identity()
    user = User.get_by_token_identity(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

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

    response_data = new_request.to_dict() if hasattr(new_request, 'to_dict') else {
        "request_id": str(new_request.request_id),
        "status": new_request.status.value,
        "user_b_contact_type": new_request.user_b_contact_type.value,
        "location_type": new_request.location_type,
        "created_at": new_request.created_at.isoformat()
    }
    
    return jsonify(response_data), 201


@meeting_requests_bp.route("", methods=["GET"])
@jwt_required()
def get_meeting_requests():
    """Get all meeting requests for the current user."""
    user_id = get_jwt_identity()
    user = User.get_by_token_identity(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    meeting_requests = MeetingRequest.query.filter_by(user_a_id=user.id).all()
    
    response_data = [request.to_dict() if hasattr(request, 'to_dict') else {
        "request_id": str(request.request_id),
        "status": request.status.value,
        "user_b_contact_type": request.user_b_contact_type.value,
        "location_type": request.location_type,
        "created_at": request.created_at.isoformat()
    } for request in meeting_requests]
    
    return jsonify(response_data), 200


@meeting_requests_bp.route("/<uuid:request_id>", methods=["GET"])
@jwt_required()
def get_meeting_request(request_id):
    """Get a specific meeting request."""
    user_id = get_jwt_identity()
    user = User.get_by_token_identity(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    meeting_request = MeetingRequest.query.get(request_id)
    if not meeting_request:
        return jsonify({"error": "Meeting request not found"}), 404

    # Only the user who created the request can view it
    if meeting_request.user_a_id != user.id:
        return jsonify({"error": "Unauthorized"}), 403

    response_data = meeting_request.to_dict() if hasattr(meeting_request, 'to_dict') else {
        "request_id": str(meeting_request.request_id),
        "status": meeting_request.status.value,
        "user_b_contact_type": meeting_request.user_b_contact_type.value,
        "location_type": meeting_request.location_type,
        "created_at": meeting_request.created_at.isoformat()
    }
    
    return jsonify(response_data), 200


@meeting_requests_bp.route("/<uuid:request_id>", methods=["PUT"])
@jwt_required()
def update_meeting_request(request_id):
    """Update a meeting request."""
    user_id = get_jwt_identity()
    user = User.get_by_token_identity(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    meeting_request = MeetingRequest.query.get(request_id)
    if not meeting_request:
        return jsonify({"error": "Meeting request not found"}), 404

    # Only the user who created the request can update it
    if meeting_request.user_a_id != user.id:
        return jsonify({"error": "Unauthorized"}), 403

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
            return jsonify({"error": "Invalid status value"}), 400

    if "meeting_location" in data:
        # TODO: Geocode meeting_location to get lat/lon
        meeting_request.selected_place_details = data["meeting_location"]

    meeting_request.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    response_data = meeting_request.to_dict() if hasattr(meeting_request, 'to_dict') else {
        "request_id": str(meeting_request.request_id),
        "status": meeting_request.status.value,
        "user_b_contact_type": meeting_request.user_b_contact_type.value,
        "location_type": meeting_request.location_type,
        "updated_at": meeting_request.updated_at.isoformat()
    }
    
    return jsonify(response_data), 200


@meeting_requests_bp.route("/<uuid:request_id>", methods=["DELETE"])
@jwt_required()
def delete_meeting_request(request_id):
    """Delete a meeting request."""
    user_id = get_jwt_identity()
    user = User.get_by_token_identity(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    meeting_request = MeetingRequest.query.get(request_id)
    if not meeting_request:
        return jsonify({"error": "Meeting request not found"}), 404

    # Only the user who created the request can delete it
    if meeting_request.user_a_id != user.id:
        return jsonify({"error": "Unauthorized"}), 403

    db.session.delete(meeting_request)
    db.session.commit()

    return "", 204


@meeting_requests_bp.route("/<uuid:request_id>/status", methods=["GET"])
@jwt_required()
def get_meeting_request_status(request_id):
    """Get the status of a meeting request."""
    user_id = get_jwt_identity()
    user = User.get_by_token_identity(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    meeting_request = MeetingRequest.query.get(request_id)
    if not meeting_request:
        return jsonify({"error": "Meeting request not found"}), 404

    # Only the user who created the request can view its status
    if meeting_request.user_a_id != user.id:
        return jsonify({"error": "Unauthorized"}), 403

    return jsonify({
        "request_id": str(request_id),
        "status": meeting_request.status.value,
        "created_at": meeting_request.created_at.isoformat(),
        "expires_at": meeting_request.expires_at.isoformat(),
    }), 200


@meeting_requests_bp.route("/<uuid:request_id>/respond", methods=["POST"])
def respond_to_meeting_request(request_id):
    """Respond to a meeting request with User B's address."""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ["token", "address_b_lat", "address_b_lon"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    meeting_request = MeetingRequest.query.get(request_id)
    if not meeting_request:
        return jsonify({"error": "Meeting request not found"}), 404

    # Verify token
    if meeting_request.token_b != data["token"]:
        return jsonify({"error": "Invalid token"}), 403

    # Check if request has expired - ensure both are timezone aware
    now = datetime.now(timezone.utc)
    expires_at = meeting_request.expires_at
    
    # If expires_at doesn't have a timezone, add UTC
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
        
    if expires_at < now:
        return jsonify({"error": "Meeting request has expired"}), 403

    # Update meeting request with address B coordinates
    meeting_request.address_b_lat = data["address_b_lat"]
    meeting_request.address_b_lon = data["address_b_lon"]
    meeting_request.status = MeetingRequestStatus.CALCULATING
    meeting_request.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    # Call process_meeting_request - this will be mocked in tests
    # The import must match the one the test is patching
    from app.utils.location import process_meeting_request as process_func
    try:
        process_func(meeting_request)
    except Exception as e:
        current_app.logger.error(f"Error processing meeting request: {e}")
    
    # Refresh meeting request from db to get current state
    db.session.refresh(meeting_request)
    
    response_data = meeting_request.to_dict() if hasattr(meeting_request, 'to_dict') else {
        "request_id": str(meeting_request.request_id),
        "status": meeting_request.status.value,
    }
    
    return jsonify(response_data), 200


@meeting_requests_bp.route("/<uuid:request_id>/results", methods=["GET"])
@jwt_required()
def get_meeting_request_results(request_id):
    """Get the results of a meeting request."""
    user_id = get_jwt_identity()
    user = User.get_by_token_identity(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    meeting_request = MeetingRequest.query.get(request_id)
    if not meeting_request:
        return jsonify({"error": "Meeting request not found"}), 404

    # Only the user who created the request can view the results
    if meeting_request.user_a_id != user.id:
        return jsonify({"error": "Unauthorized"}), 403

    suggested_options = getattr(meeting_request, 'suggested_options', None)
    selected_place_details = getattr(meeting_request, 'selected_place_details', None)

    return jsonify({
        "request_id": str(request_id),
        "status": meeting_request.status.value,
        "suggested_options": suggested_options,
        "selected_place": selected_place_details,
    }), 200
