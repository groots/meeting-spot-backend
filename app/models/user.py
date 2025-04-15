import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

import jwt
from flask import current_app
from flask_jwt_extended import create_access_token
from sqlalchemy.orm import relationship
from werkzeug.security import check_password_hash, generate_password_hash

from .. import db
from .types import UUIDType


class User(db.Model):
    """User model for storing user details."""

    __tablename__ = "users"

    id = db.Column(UUIDType(), primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256))
    google_oauth_id = db.Column(db.String(255), unique=True, nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False)

    # Relationships
    subscriptions = db.relationship("Subscription", back_populates="user", lazy=True, cascade="all, delete-orphan")
    requests_initiated = db.relationship(
        "MeetingRequest", foreign_keys="MeetingRequest.user_a_id", back_populates="user_a", lazy=True
    )
    suggested_places = db.relationship("Place", back_populates="suggested_by", lazy=True, cascade="all, delete-orphan")
    contacts = db.relationship("Contact", back_populates="user", lazy=True, cascade="all, delete-orphan")

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
        return check_password_hash(self.password_hash, password)

    def generate_access_token(self, expires_delta=None) -> str:
        """Generate a JWT token for the user."""
        if expires_delta is None:
            expires_delta = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES", 3600)

        return create_access_token(
            identity=str(self.id),
            expires_delta=expires_delta,
            additional_claims={
                "email": self.email,
            },
        )

    @classmethod
    def get_by_token_identity(cls, identity: str) -> Optional["User"]:
        """Get a user by their JWT token identity."""
        try:
            user_id = uuid.UUID(identity)
            return cls.query.get(user_id)
        except ValueError:
            return None

    def is_premium(self) -> bool:
        """Check if the user has an active premium subscription."""
        active_subscription = next(
            (sub for sub in self.subscriptions if sub.status == "active" and sub.plan_id == "premium"), None
        )
        return bool(active_subscription)

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary."""
        # Get the active subscription if available
        active_subscription = next((sub for sub in self.subscriptions if sub.status == "active"), None)

        return {
            "id": str(self.id),
            "email": self.email,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_oauth_user": bool(self.google_oauth_id),
            "is_premium": self.is_premium(),
            "subscription": active_subscription.to_dict() if active_subscription else None,
        }

    def generate_auth_token(self, expiration=86400):
        """Generate a JWT token for authentication."""
        payload = {
            "exp": datetime.utcnow() + datetime.timedelta(seconds=expiration),
            "iat": datetime.utcnow(),
            "sub": str(self.id),
        }
        token = jwt.encode(payload, current_app.config.get("JWT_SECRET_KEY"), algorithm="HS256")
        return token

    @staticmethod
    def verify_auth_token(token):
        """Verify the JWT token and return the user."""
        try:
            payload = jwt.decode(token, current_app.config.get("JWT_SECRET_KEY"), algorithms=["HS256"])
            user_id = payload["sub"]
            return User.query.filter_by(id=user_id).first()
        except:
            return None

    @staticmethod
    def identity(payload):
        user_id = payload["identity"]
        return User.query.filter_by(id=user_id).first()


# Subscription class has been moved to app/models/subscription.py


def get_user_by_token(token):
    """Get a user by their auth token."""
    try:
        # Decode the token and extract user_id
        decoded_token = jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
        user_id = decoded_token["sub"]
        return User.query.filter_by(id=user_id).first()
    except:
        return None
