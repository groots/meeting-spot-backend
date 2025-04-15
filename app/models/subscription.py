import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from .. import db
from .types import UUIDType


class Subscription(db.Model):
    """Subscription model for storing subscription details."""

    __tablename__ = "subscriptions"

    id = db.Column(UUIDType(), primary_key=True)
    user_id = db.Column(UUIDType(), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    stripe_subscription_id = db.Column(db.String(255), unique=True, nullable=True)
    stripe_customer_id = db.Column(db.String(255), nullable=True)
    plan_id = db.Column(db.String(50), nullable=False)  # 'basic', 'premium', etc.
    status = db.Column(db.String(50), nullable=False)  # 'active', 'canceled', 'trialing', etc.
    current_period_start = db.Column(db.DateTime(timezone=True), nullable=True)
    current_period_end = db.Column(db.DateTime(timezone=True), nullable=True)
    cancel_at_period_end = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False)

    # Relationships
    user = db.relationship("User", back_populates="subscriptions")

    def __init__(self, **kwargs):
        """Initialize a new subscription."""
        now = datetime.now(timezone.utc)
        kwargs.setdefault("created_at", now)
        kwargs.setdefault("updated_at", now)
        if "id" not in kwargs:
            kwargs["id"] = uuid.uuid4()
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Subscription {self.id} ({self.plan_id})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert subscription to dictionary."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "plan_id": self.plan_id,
            "status": self.status,
            "current_period_start": self.current_period_start.isoformat() if self.current_period_start else None,
            "current_period_end": self.current_period_end.isoformat() if self.current_period_end else None,
            "cancel_at_period_end": self.cancel_at_period_end,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def is_active(self) -> bool:
        """Check if subscription is active."""
        return (
            self.status == "active"
            and self.current_period_end is not None
            and self.current_period_end > datetime.now(timezone.utc)
        )
