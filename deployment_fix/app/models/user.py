import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash, generate_password_hash

from .. import db
from .types import UUIDType


class User(db.Model):
    """User model for storing user details."""

    __tablename__ = "users"

    id = db.Column(UUIDType(), primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=True)  # Allow null for OAuth users
    google_oauth_id = db.Column(db.String(255), unique=True, nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False)

    # Relationship to requests initiated by this user
    requests_initiated = db.relationship("MeetingRequest", back_populates="user_a", lazy=True)

    # Relationship to places suggested by this user
    suggested_places = db.relationship("Place", back_populates="suggested_by", lazy=True)

    def __init__(self, **kwargs):
        """Initialize a new user."""
        now = datetime.now(timezone.utc)
        kwargs.setdefault("created_at", now)
        kwargs.setdefault("updated_at", now)
        if "id" not in kwargs:
            kwargs["id"] = uuid.uuid4()
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<User {self.email}>"

    def set_password(self, password) -> None:
        """Set hashed password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password) -> bool:
        """Check if password matches hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def get_token(self) -> str:
        """Generate a JWT token for this user."""
        return create_access_token(
            identity=str(self.id), expires_delta=timedelta(days=1), additional_claims={"email": self.email}
        )

    @classmethod
    def get_by_token_identity(cls, identity: str) -> Optional["User"]:
        """Get a user by their JWT token identity."""
        try:
            user_id = uuid.UUID(identity)
            return cls.query.get(user_id)
        except ValueError:
            return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary."""
        return {
            "id": str(self.id),
            "email": self.email,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_oauth_user": bool(self.google_oauth_id),
        }
