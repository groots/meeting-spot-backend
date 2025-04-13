import uuid
from datetime import datetime

from app import db

from .types import UUIDType


class Contact(db.Model):
    """Model for storing user contacts."""

    __tablename__ = "contacts"

    id = db.Column(UUIDType(), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUIDType(), db.ForeignKey("users.id"), nullable=False)
    contact_email = db.Column(db.String(120), nullable=False)
    nickname = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_interaction = db.Column(db.DateTime)

    def to_dict(self):
        """Convert contact object to dictionary."""
        return {
            "id": str(self.id),
            "contact_email": self.contact_email,
            "nickname": self.nickname,
            "created_at": self.created_at.isoformat(),
            "last_interaction": self.last_interaction.isoformat() if self.last_interaction else None,
        }

    def __repr__(self):
        return f"<Contact {self.contact_email}>"
