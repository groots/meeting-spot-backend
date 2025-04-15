import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import relationship

from .. import db
from .types import UUIDType

# Association table for meeting requests and contacts
meeting_contacts = db.Table(
    "meeting_contacts",
    db.Column("meeting_request_id", UUIDType(), db.ForeignKey("meeting_requests.request_id", ondelete="CASCADE")),
    db.Column("contact_id", UUIDType(), db.ForeignKey("contacts.id", ondelete="CASCADE")),
    db.Column("created_at", db.DateTime(timezone=True), default=datetime.now(timezone.utc)),
)


class Contact(db.Model):
    """Contact model for storing contact information of meeting participants."""

    __tablename__ = "contacts"

    id = db.Column(UUIDType(), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUIDType(), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    company = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="contacts")
    meeting_requests = relationship("MeetingRequest", secondary=meeting_contacts, back_populates="contacts")

    def __init__(self, **kwargs):
        """Initialize a new contact."""
        now = datetime.now(timezone.utc)
        kwargs.setdefault("created_at", now)
        kwargs.setdefault("updated_at", now)
        if "id" not in kwargs:
            kwargs["id"] = uuid.uuid4()
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Contact {self.name} ({self.email})>"

    def to_dict(self):
        """Convert contact to dictionary."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "company": self.company,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
