import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from flask import current_app
from sqlalchemy import Index

from utils.encryption import decrypt_data, encrypt_data

from .. import db
from .enums import ContactType, MeetingRequestStatus
from .types import JSONType, UUIDType


class MeetingRequest(db.Model):
    """Meeting request model for storing meeting details."""

    __tablename__ = "meeting_requests"

    # Using UUID as primary key, defaulting to generating a new UUID
    request_id = db.Column(UUIDType(), primary_key=True, default=uuid.uuid4)

    # Foreign Key to User who initiated the request (can be null for anonymous)
    user_a_id = db.Column(UUIDType(), db.ForeignKey("users.id"), nullable=True)
    user_a = db.relationship("User", back_populates="requests_initiated")

    # User B contact info
    user_b_contact_type = db.Column(db.Enum(ContactType), nullable=False)
    user_b_contact_encrypted = db.Column(db.String(255), nullable=False)  # Store encrypted email/phone

    # Request details
    location_type = db.Column(db.String(50), nullable=False)  # e.g., "Restaurant / Food"

    # Coordinates
    address_a_lat = db.Column(db.Float, nullable=False)
    address_a_lon = db.Column(db.Float, nullable=False)
    address_b_lat = db.Column(db.Float, nullable=True)
    address_b_lon = db.Column(db.Float, nullable=True)

    # Status of the request
    status = db.Column(
        db.Enum(MeetingRequestStatus),
        nullable=False,
        default=MeetingRequestStatus.PENDING_B_ADDRESS,
    )

    # Secure token for User B to submit their address
    token_b = db.Column(db.String(64), unique=True, nullable=False)

    # Details of the selected place
    selected_place_google_id = db.Column(db.String(255), nullable=True)
    selected_place_details = db.Column(JSONType, nullable=True)

    # Store suggested options
    suggested_options = db.Column(JSONType, nullable=True)

    # Identifier for anonymous User A sessions
    session_identifier_a = db.Column(db.String(255), nullable=True)

    # Timestamps
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    expires_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(days=1),
    )

    # Add explicit indexes
    __table_args__ = (
        Index("ix_meeting_requests_status", "status"),
        Index("ix_meeting_requests_user_a_id", "user_a_id"),
        Index("ix_meeting_requests_token_b", "token_b"),
        Index("ix_meeting_requests_session_identifier_a", "session_identifier_a"),
    )

    @property
    def user_b_contact(self) -> Optional[str]:
        """Decrypt and return User B's contact information."""
        if not self.user_b_contact_encrypted:
            return None
        try:
            return decrypt_data(self.user_b_contact_encrypted, current_app.config.get("ENCRYPTION_KEY"))
        except ValueError as e:
            current_app.logger.error(f"Failed to decrypt contact info for request {self.request_id}: {e}")
            return None

    @user_b_contact.setter
    def user_b_contact(self, value: Optional[str]) -> None:
        """Encrypt User B's contact information before storing."""
        if not value:
            self.user_b_contact_encrypted = None
            return
        try:
            self.user_b_contact_encrypted = encrypt_data(value, current_app.config.get("ENCRYPTION_KEY"))
        except ValueError as e:
            current_app.logger.error(f"Failed to encrypt contact info: {e}")
            raise

    def __repr__(self) -> str:
        return f"<MeetingRequest {self.request_id} Status: {self.status.value}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert meeting request to dictionary."""
        return {
            "id": str(self.__dict__.get('request_id', '')),
            "user_a_id": str(self.user_a_id) if self.user_a_id else None,
            "user_b_contact_type": self.user_b_contact_type.value,
            "user_b_contact_encrypted": self.user_b_contact_encrypted,
            "location_type": self.location_type,
            "address_a_lat": self.address_a_lat,
            "address_a_lon": self.address_a_lon,
            "address_b_lat": self.address_b_lat,
            "address_b_lon": self.address_b_lon,
            "status": self.status.value,
            "token_b": self.token_b,
            "selected_place_google_id": self.selected_place_google_id,
            "selected_place_details": self.selected_place_details,
            "suggested_options": self.suggested_options,
            "session_identifier_a": self.session_identifier_a,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }
