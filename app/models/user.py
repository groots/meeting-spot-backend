import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from werkzeug.security import check_password_hash, generate_password_hash

from .. import db
from .types import UUIDType


class User(db.Model):
    """User model for storing user details."""

    __tablename__ = "users"

    id = db.Column(UUIDType(), primary_key=True, default=uuid.uuid4)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)  # Store hashed passwords
    google_oauth_id = db.Column(db.String(255), unique=True, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship to requests initiated by this user
    requests_initiated = db.relationship("MeetingRequest", back_populates="user_a", lazy=True)

    # Relationship to places suggested by this user
    suggested_places = db.relationship("Place", back_populates="suggested_by", lazy=True)

    def __repr__(self) -> str:
        return f"<User {self.email}>"

    def set_password(self, password) -> None:
        """Set hashed password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password) -> bool:
        """Check if password matches hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary."""
        return {
            "id": str(self.id),
            "email": self.email,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
