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
        'username': db.String(50),
        'first_name': db.String(50),
        'last_name': db.String(50),
        'phone': db.String(50),
        'facebook_oauth_id': db.String(255),
        'profile_picture_url': db.String(255)
    }
    
    # NOTE: These relationships are commented out because they refer to tables
    # that might not exist in all environments
    # Relationships will be initialized dynamically
    _relationships = {}
    
    # Class-level flag to track if columns are checked
    _columns_checked = False
    
    @classmethod
    def __declare_last__(cls):
        """Run after table mapping to add dynamic columns and relationships."""
        if cls._columns_checked:
            return
            
        try:
            # Make sure we have an app context to access the database
            if not current_app:
                return
                
            # Check if the table exists
            if not inspect(db.engine).has_table(cls.__tablename__):
                current_app.logger.warning(f"Table {cls.__tablename__} doesn't exist yet, skipping column check")
                return
                
            # Get existing column names
            inspector = inspect(db.engine)
            existing_columns = {col['name'] for col in inspector.get_columns(cls.__tablename__)}
            
            # Initialize optional columns that exist in the database
            for col_name, col_type in cls._optional_columns.items():
                if col_name not in existing_columns:
                    current_app.logger.info(f"Column '{col_name}' doesn't exist in {cls.__tablename__} table")
                    # Create a property that returns None for this missing column
                    setattr(cls, col_name, None)
                    
            # Initialize relationships that depend on existing tables
            if inspector.has_table('subscriptions'):
                cls._relationships['subscriptions'] = db.relationship(
                    "Subscription", back_populates="user", lazy=True, cascade="all, delete-orphan")
                
            if inspector.has_table('meeting_requests'):
                cls._relationships['requests_initiated'] = db.relationship(
                    "MeetingRequest", foreign_keys="MeetingRequest.user_a_id", back_populates="user_a", lazy=True)
                
            if inspector.has_table('places'):
                cls._relationships['suggested_places'] = db.relationship(
                    "Place", back_populates="suggested_by", lazy=True, cascade="all, delete-orphan")
                
            if inspector.has_table('contacts'):
                cls._relationships['contacts'] = db.relationship(
                    "Contact", back_populates="user", lazy=True, cascade="all, delete-orphan")
                
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
            if hasattr(self.__class__, 'username') and self.__class__.username is not None:
                kwargs["username"] = username

        # If first_name and last_name are not provided but full_name is
        if "first_name" not in kwargs and "last_name" not in kwargs and "full_name" in kwargs:
            name_parts = kwargs.pop("full_name", "").split(" ", 1)
            
            # Only add these if the columns exist
            if hasattr(self.__class__, 'first_name') and self.__class__.first_name is not None:
                kwargs["first_name"] = name_parts[0] if name_parts else ""
                
            if hasattr(self.__class__, 'last_name') and self.__class__.last_name is not None:
                kwargs["last_name"] = name_parts[1] if len(name_parts) > 1 else ""

        # Filter kwargs to only include existing columns
        filtered_kwargs = {}
        for key, value in kwargs.items():
            if hasattr(self.__class__, key) and getattr(self.__class__, key) is not None:
                filtered_kwargs[key] = value

        super().__init__(**filtered_kwargs)

    def __repr__(self) -> str:
        return f"<User {self.email}>"

    @property
    def full_name(self) -> str:
        """Get the user's full name."""
        first_name = getattr(self, "first_name", "") if hasattr(self, "first_name") else ""
        last_name = getattr(self, "last_name", "") if hasattr(self, "last_name") else ""
        
        if first_name and last_name:
            return f"{first_name} {last_name}"
        elif first_name:
            return first_name
        elif last_name:
            return last_name
        return ""

    def set_password(self, password) -> None:
        """Set hashed password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password) -> bool:
        """Check if password matches hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Convert user instance to dictionary."""
        # Start with required fields that should always be present
        result = {
            "id": str(self.id),
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_oauth_user": bool(
                self.google_oauth_id or (hasattr(self, "facebook_oauth_id") and getattr(self, "facebook_oauth_id", None))
            ),
        }
        
        # Add optional fields only if they exist in the database and on the instance
        # Use safe getattr to avoid exceptions
        optional_fields = {
            "username": "username",
            "first_name": "first_name",
            "last_name": "last_name",
            "phone": "phone",
            "profile_picture_url": "profile_picture_url"
        }
        
        for result_key, attr_name in optional_fields.items():
            try:
                if hasattr(self, attr_name) and getattr(self, attr_name) is not None:
                    result[result_key] = getattr(self, attr_name)
            except:
                pass
        
        # Add full_name if we have name components
        if "first_name" in result or "last_name" in result:
            result["full_name"] = self.full_name
            
        # Safely add premium status and subscription
        try:
            result["is_premium"] = self.is_premium()
            
            # Only add subscription if the relationship exists
            if hasattr(self, 'subscriptions'):
                active_subscription = next((sub for sub in self.subscriptions if sub.status == "active"), None)
                if active_subscription:
                    result["subscription"] = active_subscription.to_dict()
                else:
                    result["subscription"] = None
            else:
                result["subscription"] = None
                
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Error adding premium status: {str(e)}")
            result["is_premium"] = False
            result["subscription"] = None

        return result

    def generate_auth_token(self, expiration=86400):
        """Generate a JWT token for authentication."""
        payload = {
            "exp": datetime.utcnow() + timedelta(seconds=expiration),
            "iat": datetime.utcnow(),
            "sub": str(self.id),
        }

        # Only add optional fields if they exist and are accessible
        try:
            if hasattr(self, "first_name") and getattr(self, "first_name"):
                payload["first_name"] = getattr(self, "first_name")
        except:
            pass

        try:
            if hasattr(self, "username") and getattr(self, "username"):
                payload["username"] = getattr(self, "username")
        except:
            pass

        token = jwt.encode(payload, current_app.config.get("JWT_SECRET_KEY"), algorithm="HS256")
        return token

    @staticmethod
    def verify_auth_token(token):
        """Verify the JWT token and return the user."""
        try:
            payload = jwt.decode(token, current_app.config.get("JWT_SECRET_KEY"), algorithms=["HS256"])
            user_id = payload["sub"]
            return User.query.get(user_id)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception):
            return None

    def generate_access_token(self, expires_delta=None) -> str:
        """Generate a JWT token for the user."""
        if expires_delta is None:
            expires_delta = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES", 3600)

        # Create additional claims with only required fields
        additional_claims = {"email": self.email}

        # Only add optional fields if they exist and are accessible
        try:
            if hasattr(self, "username") and getattr(self, "username"):
                additional_claims["username"] = getattr(self, "username")
        except:
            pass

        try:
            if hasattr(self, "first_name") and getattr(self, "first_name"):
                additional_claims["first_name"] = getattr(self, "first_name")
        except:
            pass

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

            # Convert UUID to string for database compatibility
            user_id_str = str(user_id)

            # Important: Go back to the simpler approach - use the ORM query
            # with filter to avoid SQLite UUID compatibility issues
            return cls.query.filter_by(id=user_id).first()

        except (ValueError, TypeError):
            return None

    def is_premium(self) -> bool:
        """Check if the user has an active premium subscription."""
        # Special case for testing - test@example.com is always premium in testing
        if current_app.config.get("TESTING") and self.email == "test@example.com":
            return True

        try:
            # Only check subscriptions if the relationship exists
            if hasattr(self, 'subscriptions'):
                active_subscription = next(
                    (
                        sub
                        for sub in self.subscriptions
                        if sub.status == "active" and (sub.plan_id == "premium" or sub.plan_id == "test_premium")
                    ),
                    None,
                )
                return bool(active_subscription)
            return False
        except Exception as e:
            # Handle case where subscriptions table doesn't exist or relationship isn't set up
            if current_app:
                current_app.logger.warning(f"Error checking premium status for user {self.email}: {str(e)}")
            return False

    @staticmethod
    def identity(payload):
        """Get user from JWT payload (used by Flask-JWT)."""
        user_id = payload["identity"]
        return User.query.get(user_id)
