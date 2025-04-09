"""Tests for MeetingRequest model."""

from datetime import datetime, timezone

import pytest

from app.models import ContactType, MeetingRequest, MeetingRequestStatus


def test_meeting_request_encryption(app, _session):
    """Test that contact information is properly encrypted."""
    contact_email = "test@example.com"
    request = MeetingRequest(
        user_b_contact_type=ContactType.EMAIL,
        user_b_contact=contact_email,
        location_type="cafe",
        status=MeetingRequestStatus.PENDING_B_ADDRESS,
    )

    # Verify encryption happened
    assert request.user_b_contact_encrypted != contact_email
    assert request.user_b_contact == contact_email  # Should decrypt automatically

    # Test persistence
    _session.add(request)
    _session.commit()

    # Fetch from DB and verify
    fetched = MeetingRequest.query.get(request.request_id)
    assert fetched.user_b_contact == contact_email
    assert fetched.user_b_contact_encrypted != contact_email


def test_meeting_request_missing_encryption_key(app):
    """Test that model fails gracefully with missing encryption key."""
    app.config["ENCRYPTION_KEY"] = None

    with pytest.raises(ValueError, match="Encryption key is required"):
        MeetingRequest(
            user_b_contact_type=ContactType.EMAIL,
            user_b_contact="test@example.com",
            location_type="cafe",
            status=MeetingRequestStatus.PENDING_B_ADDRESS,
        )
