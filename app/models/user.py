import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

import jwt
from flask import current_app
from flask_jwt_extended import create_access_token
from sqlalchemy import Column, inspect, text
from sqlalchemy.orm import relationship
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

    # Required columns that should exist in all database versions
    password_hash = db.Column(db.String(256))
    google_oauth_id = db.Column(db.String(255), unique=True, nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False)

    # Define optional columns that might be missing in some database instances
    # These will only be used if they exist in the database
    _optional_columns = {
        "username": db.String(50),
        "first_name": db.String(50),
        "last_name": db.String(50),
        "phone": db.String(50),
        "facebook_oauth_id": db.String(255),
        "profile_picture_url": db.String(255),
    }

    # Define relationship placeholders, which will be properly initialized later if the tables exist
    # This prevents errors when related models are missing
    requests_initiated = None
    contacts = None
    suggested_places = None
    subscriptions = None

    # Class-level flag to track if columns are checked
    _columns_checked = False

    @classmethod
    def __declare_last__(cls):
        """Run after table mapping to add dynamic columns and relationships."""
        # Skip initialization if already checked
        if cls._columns_checked:
            return

        try:
            # Get DB inspector to check table structure
            inspector = inspect(db.engine)

            # Only proceed if users table exists
            if not inspector.has_table("users"):
                return

            # Get actual columns from the database
            table_columns = {col["name"] for col in inspector.get_columns("users")}

            # Check which optional columns exist and add them
            for col_name, col_type in cls._optional_columns.items():
                if col_name in table_columns:
                    setattr(cls, col_name, db.Column(col_type))

            # Add relationships if related tables exist
            if inspector.has_table("meeting_requests"):
                # Add requests_initiated relationship
                cls.requests_initiated = db.relationship(
                    "MeetingRequest",
                    back_populates="user_a",
                    foreign_keys="MeetingRequest.user_a_id",
                    lazy=True,
                    cascade="all, delete-orphan",
                )

            # Check if places table exists before defining the relationship
            if inspector.has_table("places"):
                try:
                    # Try to import the Place model first to make sure it's loaded
                    from .place import Place

                    # Define the relationship
                    cls.suggested_places = db.relationship(
                        "Place", back_populates="suggested_by", lazy=True, cascade="all, delete-orphan"
                    )
                except (ImportError, AttributeError) as e:
                    # If Place model isn't available, log the error but don't fail
                    if current_app:
                        current_app.logger.warning(f"Place model not available for relationship: {str(e)}")

            # Check if contacts table exists before defining the relationship
            if inspector.has_table("contacts"):
                cls.contacts = db.relationship(
                    "Contact", back_populates="user", lazy=True, cascade="all, delete-orphan"
                )

            # Check if subscriptions table exists before defining the relationship
            if inspector.has_table("subscriptions"):
                try:
                    # Try to import the Subscription model first to make sure it's loaded
                    from .subscription import Subscription

                    # Define the relationship
                    cls.subscriptions = db.relationship(
                        "Subscription", back_populates="user", lazy=True, cascade="all, delete-orphan"
                    )
                except (ImportError, AttributeError) as e:
                    # If Subscription model isn't available, log the error but don't fail
                    if current_app:
                        current_app.logger.warning(f"Subscription model not available for relationship: {str(e)}")

            cls._columns_checked = True

        except Exception as e:
            if current_app:
                current_app.logger.error(f"Error initializing User model: {str(e)}")

    def __init__(self, **kwargs):
        """Initialize a new user."""
        now = datetime.now(timezone.utc)
        kwargs.setdefault("created_at", now)
        kwargs.setdefault("updated_at", now)
        if "id" not in kwargs:
            kwargs["id"] = uuid.uuid4()

        # Generate username from email if not provided and column exists
        if "username" not in kwargs and "email" in kwargs:
            username = kwargs["email"].split("@")[0]

            # Only add username if the column exists
            if hasattr(self.__class__, "username") and self.__class__.username is not None:
                kwargs["username"] = username

        # If first_name and last_name are not provided but full_name is
        if "first_name" not in kwargs and "last_name" not in kwargs and "full_name" in kwargs:
            name_parts = kwargs.pop("full_name", "").split(" ", 1)

            # Only add these if the columns exist
            if hasattr(self.__class__, "first_name") and self.__class__.first_name is not None:
                kwargs["first_name"] = name_parts[0] if name_parts else ""

            if hasattr(self.__class__, "last_name") and self.__class__.last_name is not None:
                kwargs["last_name"] = name_parts[1] if len(name_parts) > 1 else ""

        # Filter out kwargs that don't match columns
        valid_kwargs = {}
        for key, value in kwargs.items():
            if hasattr(self.__class__, key):
                valid_kwargs[key] = value

        super().__init__(**valid_kwargs)

    def __repr__(self):
        """Return a string representation of the user."""
        return f"<User {self.email}>"

    def set_password(self, password):
        """Set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the user's password."""
        return check_password_hash(self.password_hash, password)

    def generate_auth_token(self, expiration=86400):
        """Generate an authentication token."""
        payload = {"id": str(self.id), "exp": datetime.now(timezone.utc) + timedelta(seconds=expiration)}
        return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")

    def generate_access_token(self, additional_claims=None):
        """Generate a JWT access token for the user."""
        claims = {"is_admin": getattr(self, "is_admin", False)} if additional_claims is None else additional_claims
        return create_access_token(identity=str(self.id), additional_claims=claims)

    @classmethod
    def verify_relationships(cls):
        """Verify that relationships are properly set up."""
        from flask import current_app
        from sqlalchemy import inspect

        try:
            inspector = inspect(db.engine)

            # Check if subscriptions table exists and set up relationship if needed
            if inspector.has_table("subscriptions") and not hasattr(cls, "subscriptions"):
                try:
                    # Import the Subscription model
                    from .subscription import Subscription

                    # Set up the relationship if it doesn't exist
                    cls.subscriptions = db.relationship(
                        "Subscription", back_populates="user", lazy=True, cascade="all, delete-orphan"
                    )

                    if current_app:
                        current_app.logger.info("User-Subscription relationship established in verify_relationships")
                except (ImportError, AttributeError) as e:
                    if current_app:
                        current_app.logger.warning(f"Could not set up Subscription relationship in verify: {str(e)}")

        except Exception as e:
            if current_app:
                current_app.logger.error(f"Error verifying User relationships: {str(e)}")

    def is_premium(self):
        """Check if the user has a premium subscription."""
        # Check if subscription relationship exists
        if not hasattr(self.__class__, "subscriptions"):
            # Default to True for development/testing, False for production
            from flask import current_app

            return current_app.config.get("FLASK_ENV") != "production"

        try:
            if self.subscriptions is None:
                return False

            active_sub = next((sub for sub in self.subscriptions if sub.is_active()), None)
            return active_sub is not None
        except Exception as e:
            # Log error and default to True in development
            from flask import current_app

            if current_app:
                current_app.logger.error(f"Error checking premium status: {str(e)}")
            return current_app.config.get("FLASK_ENV") != "production"

    def to_dict(self):
        """Convert user object to dictionary with safe attributes."""
        user_dict = {
            "id": str(self.id),
            "email": self.email,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_premium": self.is_premium(),
        }

        # Add optional fields if they exist in the model
        optional_fields = [
            "username",
            "first_name",
            "last_name",
            "phone",
            "profile_picture_url",
        ]

        for field in optional_fields:
            if hasattr(self, field) and getattr(self, field) is not None:
                user_dict[field] = getattr(self, field)

        # Combine first and last name into full_name if both exist
        if hasattr(self, "first_name") and hasattr(self, "last_name"):
            if self.first_name and self.last_name:
                user_dict["full_name"] = f"{self.first_name} {self.last_name}"
            elif self.first_name:
                user_dict["full_name"] = self.first_name
            elif self.last_name:
                user_dict["full_name"] = self.last_name

        return user_dict

    @classmethod
    def verify_auth_token(cls, token):
        """Verify an authentication token."""
        try:
            payload = jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
            user = cls.query.get(payload["id"])
            return user
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception):
            return None
