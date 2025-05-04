import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

from flask import current_app
from sqlalchemy import Column, ForeignKey, Index, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import column_property, relationship

from app.utils.encryption import decrypt_data, encrypt_data

from .. import db
from .enums import ContactType, MeetingRequestStatus
from .place import Place
from .types import JSONType, UUIDType

# Association table for meeting request suggested places
meeting_request_suggested_places = Table(
    "meeting_request_suggested_places",
    db.metadata,
    db.Column("meeting_request_id", UUIDType(), db.ForeignKey("meeting_requests.request_id"), primary_key=True),
    db.Column("place_id", UUIDType(), db.ForeignKey("places.id"), primary_key=True),
    db.Column("created_at", db.DateTime, server_default=db.func.now()),
)


class MeetingRequest(db.Model):
    """Meeting request model for storing meeting details."""

    __tablename__ = "meeting_requests"

    # Using UUID as primary key, defaulting to generating a new UUID
    request_id = Column(UUIDType(), primary_key=True, default=uuid.uuid4)

    # Foreign Key to User who initiated the request (can be null for anonymous)
    user_a_id = Column(UUIDType(), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    user_a = relationship("User", back_populates="requests_initiated")

    # User B contact info
    user_b_contact_type = Column(db.Enum(ContactType), nullable=False)
    user_b_contact_encrypted = Column(db.String(255), nullable=False)  # Store encrypted email/phone

    # Add user_b_email as a hybrid property that doesn't create DB column
    # but maintains backward compatibility with tests
    @hybrid_property
    def user_b_email(self) -> Optional[str]:
        """Get user B's email (if contact type is email)."""
        if self.user_b_contact_type == ContactType.EMAIL:
            return self.user_b_contact
        return None

    @user_b_email.setter
    def user_b_email(self, value: Optional[str]) -> None:
        """Set user B's email and contact type."""
        if value:
            self.user_b_contact_type = ContactType.EMAIL
            self.user_b_contact = value

    # Add user_b_name as a hybrid property that doesn't create a DB column
    # It will store the name in the encrypted contact data or in the associated contact
    _user_b_name_value = None

    @hybrid_property
    def user_b_name(self) -> Optional[str]:
        """Get user B's name."""
        # Try to get from runtime-stored value
        if self._user_b_name_value:
            return self._user_b_name_value

        # Try to get from associated contact if any
        for contact in self.contacts:
            if contact.email == self.user_b_email:
                return contact.name

        return ""

    @user_b_name.setter
    def user_b_name(self, value: Optional[str]) -> None:
        """Set user B's name."""
        self._user_b_name_value = value or ""

    # Request details
    location_type = Column(db.String(50), nullable=False)  # e.g., "Restaurant / Food"
    location_a = Column(JSONType, nullable=False)
    location_b = Column(JSONType, nullable=True)

    # Coordinates
    address_a_lat = Column(db.Float, nullable=False)
    address_a_lon = Column(db.Float, nullable=False)
    address_b_lat = Column(db.Float, nullable=True)
    address_b_lon = Column(db.Float, nullable=True)

    # Status of the request
    status = Column(
        db.Enum(MeetingRequestStatus),
        nullable=False,
        default=MeetingRequestStatus.PENDING_B_ADDRESS,
    )

    # Secure token for User B to submit their address
    token_b = Column(db.String(64), unique=True, nullable=False)

    # Details of the selected place
    selected_place_google_id = Column(db.String(255), nullable=True)
    selected_place_details = Column(JSONType, nullable=True)

    # Store suggested options
    suggested_options = Column(JSONType, nullable=True)

    # Identifier for anonymous User A sessions
    session_identifier_a = Column(db.String(255), nullable=True)

    # Place relationships
    selected_place_id = Column(UUIDType(), ForeignKey("places.id"), nullable=True)
    selected_place = relationship(
        "Place",
        back_populates="selected_by_meetings",
        uselist=False,
    )

    suggested_places = relationship(
        "Place", secondary=meeting_request_suggested_places, back_populates="suggested_for_meetings"
    )

    # Timestamps
    created_at = Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    expires_at = Column(
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

    # Relationship to contacts via the association table
    contacts = relationship("Contact", secondary="meeting_contacts", back_populates="meeting_requests")

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
        user_b_contact = next((c for c in self.contacts if c.email == self.user_b_email), None)

        result = {
            "request_id": str(self.request_id),
            "user_a_id": str(self.user_a_id) if self.user_a_id else None,
            "user_b_contact_type": self.user_b_contact_type.value,
            "user_b_contact_encrypted": self.user_b_contact_encrypted,
            "user_b_name": self.user_b_name,
            "user_b_email": self.user_b_email,  # Include for backwards compatibility
            "location_type": self.location_type,
            "address_a_lat": self.address_a_lat,
            "address_a_lon": self.address_a_lon,
            "address_b_lat": self.address_b_lat,
            "address_b_lon": self.address_b_lon,
            "status": self.status.value,
            "token_b": self.token_b,
            "selected_place_id": str(self.selected_place_id) if self.selected_place_id else None,
            "selected_place": self.selected_place.to_dict() if self.selected_place else None,
            "suggested_places": [place.to_dict() for place in self.suggested_places] if self.suggested_places else [],
            "selected_place_google_id": self.selected_place_google_id,
            "selected_place_details": self.selected_place_details,
            "suggested_options": self.suggested_options,
            "session_identifier_a": self.session_identifier_a,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "is_expired": self.is_expired(),
        }

        # Add contact details if available
        if user_b_contact:
            result["user_b_contact"] = {
                "id": str(user_b_contact.id),
                "name": user_b_contact.name,
                "email": user_b_contact.email,
                "phone": user_b_contact.phone,
                "company": user_b_contact.company,
            }

        return result

    def is_expired(self) -> bool:
        """Check if the meeting request has expired."""
        if not self.expires_at:
            return False

        # Convert both to naive UTC datetimes for comparison
        current_time = datetime.utcnow()
        expires_at_naive = self.expires_at.replace(tzinfo=None) if self.expires_at.tzinfo else self.expires_at

        return current_time > expires_at_naive

    @staticmethod
    def create_from_dict(data: Dict[str, Any], user_id: uuid.UUID) -> "MeetingRequest":
        """Create a new meeting request from dictionary data."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)  # Default to 7 days

        location_a = {
            "address": data.get("location_a", {}).get("address", ""),
            "latitude": data.get("location_a", {}).get("latitude"),
            "longitude": data.get("location_a", {}).get("longitude"),
        }

        categories = data.get("categories", None)

        # Get user_b_email for backward compatibility
        user_b_email = data.get("user_b_email", "").lower() if "user_b_email" in data else None

        # Create instance with either user_b_contact or user_b_email
        if user_b_email:
            mr = MeetingRequest(
                user_a_id=user_id,
                user_b_email=user_b_email,  # This will set user_b_contact and user_b_contact_type
                user_b_name=data.get("user_b_name", ""),
                location_a=location_a,
                location_type=data.get("location_type", ""),
                address_a_lat=data.get("location_a", {}).get("latitude"),
                address_a_lon=data.get("location_a", {}).get("longitude"),
                address_b_lat=data.get("location_b", {}).get("latitude"),
                address_b_lon=data.get("location_b", {}).get("longitude"),
                status=data.get("status", MeetingRequestStatus.PENDING_B_ADDRESS),
                expires_at=expires_at,
                token_b=uuid.uuid4().hex,  # Ensure token_b is always set
            )
        else:
            # Handle case without user_b_email (not expected but robust)
            mr = MeetingRequest(
                user_a_id=user_id,
                user_b_contact_type=ContactType.EMAIL,  # Default
                user_b_contact=data.get("user_b_contact", ""),
                user_b_name=data.get("user_b_name", ""),
                location_a=location_a,
                location_type=data.get("location_type", ""),
                address_a_lat=data.get("location_a", {}).get("latitude"),
                address_a_lon=data.get("location_a", {}).get("longitude"),
                address_b_lat=data.get("location_b", {}).get("latitude"),
                address_b_lon=data.get("location_b", {}).get("longitude"),
                status=data.get("status", MeetingRequestStatus.PENDING_B_ADDRESS),
                expires_at=expires_at,
                token_b=uuid.uuid4().hex,  # Ensure token_b is always set
            )

        return mr


undefined
