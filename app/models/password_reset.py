import secrets
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


class PasswordReset(db.Model):
    __tablename__ = "password_resets"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

    # Relationship
    user = db.relationship("User", backref=db.backref("password_resets", lazy="dynamic"))

    def __init__(self, user_id, token, expires_in=24):
        self.user_id = user_id
        self.token = token
        self.expires_at = datetime.utcnow() + timedelta(hours=expires_in)

    def __repr__(self):
        return f"<PasswordReset {self.token}>"

    def is_expired(self):
        return datetime.utcnow() > self.expires_at

    def is_valid(self):
        """
        Check if this password reset token is valid (not expired and not used).

        Returns:
            bool: True if valid, False otherwise
        """
        return not self.is_expired() and not self.used

    def use(self):
        """
        Mark this password reset token as used.
        """
        self.used = True

    @classmethod
    def create_for_user(cls, user_id, expires_in=1):
        """
        Create a new password reset token for a user.

        Args:
            user_id: The user's ID
            expires_in: Hours until the token expires (default: 1)

        Returns:
            PasswordReset: The created password reset object
        """
        # Generate a secure token
        token = secrets.token_urlsafe(32)

        # Create and save the reset
        reset = cls(user_id=user_id, token=token, expires_in=expires_in)
        db.session.add(reset)

        return reset

    @classmethod
    def get_by_token(cls, token):
        """
        Get a password reset by token.

        Args:
            token: The reset token

        Returns:
            PasswordReset or None: The password reset object if found, None otherwise
        """
        return cls.query.filter_by(token=token).first()

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "token": self.token,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "used": self.used,
        }
