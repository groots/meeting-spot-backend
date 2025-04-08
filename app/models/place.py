from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .. import db
from .types import UUIDType

# Association table for many-to-many relationship between MeetingRequest and Place
meeting_request_selected_places = Table(
    "meeting_request_selected_places",
    db.metadata,
    Column("meeting_request_id", UUIDType(), ForeignKey("meeting_requests.request_id")),
    Column("place_id", UUIDType(), ForeignKey("places.id")),
)


class Place(db.Model):
    """Model for storing place information."""

    __tablename__ = "places"

    id = db.Column(UUIDType(), primary_key=True, default=uuid4)
    name = db.Column(db.String, nullable=False)
    address = db.Column(db.String, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    google_place_id = db.Column(db.String, unique=True)

    # Who suggested this place
    suggested_by_id = db.Column(UUIDType(), db.ForeignKey("users.id"), nullable=False)
    suggested_by = db.relationship("User", back_populates="suggested_places")

    # Meeting requests that suggested this place
    suggested_for_meetings = db.relationship(
        "MeetingRequest", secondary="meeting_request_suggested_places", back_populates="suggested_places"
    )

    # Meeting requests that selected this place
    selected_by_meetings = db.relationship(
        "MeetingRequest", foreign_keys="[MeetingRequest.selected_place_id]", back_populates="selected_place"
    )

    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=db.func.now())

    def to_dict(self):
        """Convert the place to a dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "address": self.address,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "google_place_id": self.google_place_id,
            "suggested_by_id": str(self.suggested_by_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
