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

    # Stripe and subscription related fields
    stripe_customer_id = db.Column(db.String(255), unique=True, nullable=True)
    subscription_plan = db.Column(db.String(50), nullable=True)  # 'free', 'basic', 'premium'
    subscription_status = db.Column(db.String(50), nullable=True)  # 'active', 'canceled', 'trialing', etc.
    subscription_end_date = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    subscriptions = db.relationship("Subscription", back_populates="user", lazy=True)

    # Relationship to requests initiated by this user
    requests_initiated = db.relationship("MeetingRequest", back_populates="user_a", lazy=True)

    # Relationship to places suggested by this user
    suggested_places = db.relationship("Place", back_populates="suggested_by", lazy=True)

    # Relationship to contacts
    contacts = db.relationship("Contact", back_populates="user", lazy=True, cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        """Initialize a new user."""
        now = datetime.now(timezone.utc)
        kwargs.setdefault("created_at", now)
        kwargs.setdefault("updated_at", now)
        kwargs.setdefault("subscription_plan", "free")  # Default to free plan
        if "id" not in kwargs:
            kwargs["id"] = uuid.uuid4()
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<User {self.email}>"

    def set_password(self, password) -> None:
        """Set hashed password."""
        # Use method='pbkdf2:sha1' to generate a shorter hash (default is pbkdf2:sha256)
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha1")

    def check_password(self, password) -> bool:
        """Check if password matches hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def get_token(self) -> str:
        """Generate a JWT token for this user."""
        return create_access_token(
            identity=str(self.id),
            expires_delta=timedelta(days=1),
            additional_claims={
                "email": self.email,
                "subscription_plan": self.subscription_plan,
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
        # First check subscriptions relationship
        for subscription in self.subscriptions:
            if subscription.is_active() and subscription.plan_id in ["premium", "pro"]:
                return True

        # Fallback to legacy fields
        return (
            self.subscription_plan in ["premium", "pro"]
            and self.subscription_status == "active"
            and (self.subscription_end_date is None or self.subscription_end_date > datetime.now(timezone.utc))
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary."""
        return {
            "id": str(self.id),
            "email": self.email,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_oauth_user": bool(self.google_oauth_id),
            "subscription_plan": self.subscription_plan,
            "subscription_status": self.subscription_status,
            "subscription_end_date": self.subscription_end_date.isoformat() if self.subscription_end_date else None,
            "is_premium": self.is_premium(),
        }


# Subscription class has been moved to app/models/subscription.py
