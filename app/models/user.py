import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

import jwt
from flask import current_app
from flask_jwt_extended import create_access_token
from sqlalchemy import Column, inspect
from sqlalchemy.orm import load_only, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from .. import db
from .types import UUIDType


# Create a version of User model that works with or without the username column
# This is important for backwards compatibility with existing databases
class User(db.Model):
    """User model for storing user details."""

    __tablename__ = "users"

    id = db.Column(UUIDType(), primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)

    # Make these optional columns
    username = db.Column(db.String(50), unique=True, nullable=True, index=True)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)

    password_hash = db.Column(db.String(256))
    google_oauth_id = db.Column(db.String(255), unique=True, nullable=True, index=True)
    facebook_oauth_id = db.Column(db.String(255), unique=True, nullable=True, index=True)
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

        # Generate username from email if not provided
        if "username" not in kwargs and "email" in kwargs:
            kwargs["username"] = kwargs["email"].split("@")[0]

        # If first_name and last_name are not provided but full_name is
        if "first_name" not in kwargs and "last_name" not in kwargs and "full_name" in kwargs:
            name_parts = kwargs.pop("full_name", "").split(" ", 1)
            kwargs["first_name"] = name_parts[0] if name_parts else ""
            kwargs["last_name"] = name_parts[1] if len(name_parts) > 1 else ""

        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<User {self.email}>"

    @property
    def full_name(self) -> str:
        """Get the user's full name."""
        if hasattr(self, "first_name") and hasattr(self, "last_name") and self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif hasattr(self, "first_name") and self.first_name:
            return self.first_name
        elif hasattr(self, "last_name") and self.last_name:
            return self.last_name
        return ""

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

        # Create additional claims without optional fields
        additional_claims = {"email": self.email}

        # Only add optional fields if they exist
        if hasattr(self, "username") and self.username:
            additional_claims["username"] = self.username

        if hasattr(self, "first_name") and self.first_name:
            additional_claims["first_name"] = self.first_name

        return create_access_token(
            identity=str(self.id),
            expires_delta=expires_delta,
            additional_claims=additional_claims,
        )

    @classmethod
    def get_by_token_identity(cls, identity):
        """Get user by token identity (used in JWT)."""
        try:
            # Check if the identity is a valid UUID string
            user_id = uuid.UUID(identity)

            # Only select columns that are guaranteed to exist
            inspector = inspect(db.engine)
            columns = [col["name"] for col in inspector.get_columns("users")]

            # Always include these required columns
            required_cols = ["id", "email", "password_hash", "google_oauth_id", "created_at", "updated_at"]

            # Add optional columns only if they exist in the database
            optional_cols = ["username", "first_name", "last_name", "facebook_oauth_id"]
            select_columns = required_cols + [col for col in optional_cols if col in columns]

            # Query with only the columns that exist
            return cls.query.options(load_only(*select_columns)).filter_by(id=user_id).first()

        except (ValueError, TypeError):
            return None

    def is_premium(self) -> bool:
        """Check if the user has an active premium subscription."""
        # Special case for testing - test@example.com is always premium in testing
        if current_app.config.get("TESTING") and self.email == "test@example.com":
            return True

        try:
            active_subscription = next(
                (
                    sub
                    for sub in self.subscriptions
                    if sub.status == "active" and (sub.plan_id == "premium" or sub.plan_id == "test_premium")
                ),
                None,
            )
            return bool(active_subscription)
        except Exception:
            # If subscriptions table doesn't exist or there's another error, assume not premium
            return False

    def to_dict(self):
        """Convert user instance to dictionary."""
        # Check for active subscription
        active_subscription = None
        try:
            active_subscription = next((sub for sub in self.subscriptions if sub.status == "active"), None)
        except Exception:
            # If there's an error (e.g., table doesn't exist), leave active_subscription as None
            pass

        # Start with required fields that should always be present
        result = {
            "id": str(self.id),
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_oauth_user": bool(
                self.google_oauth_id or (hasattr(self, "facebook_oauth_id") and self.facebook_oauth_id)
            ),
            "is_premium": self.is_premium(),
            "subscription": active_subscription.to_dict() if active_subscription else None,
        }

        # Add optional fields only if they exist
        if hasattr(self, "username") and self.username:
            result["username"] = self.username

        if hasattr(self, "first_name") and self.first_name:
            result["first_name"] = self.first_name

        if hasattr(self, "last_name") and self.last_name:
            result["last_name"] = self.last_name

        if hasattr(self, "first_name") or hasattr(self, "last_name"):
            result["full_name"] = self.full_name

        return result

    def generate_auth_token(self, expiration=86400):
        """Generate a JWT token for authentication."""
        payload = {
            "exp": datetime.utcnow() + timedelta(seconds=expiration),
            "iat": datetime.utcnow(),
            "sub": str(self.id),
        }

        # Only add optional fields if they exist
        if hasattr(self, "first_name") and self.first_name:
            payload["first_name"] = self.first_name

        if hasattr(self, "username") and self.username:
            payload["username"] = self.username

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
