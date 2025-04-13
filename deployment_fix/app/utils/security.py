"""Security utilities for the application."""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash


def generate_password(password: str) -> str:
    """
    Generate a secure password hash.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        password: Plain text password
        password_hash: Hashed password

    Returns:
        True if password matches, False otherwise
    """
    return check_password_hash(password_hash, password)


def generate_token(
    user_id: str,
    expires_in: Optional[int] = None,
    token_type: str = "access",
) -> str:
    """
    Generate a JWT token.

    Args:
        user_id: User ID
        expires_in: Token expiration time in seconds
        token_type: Type of token (access or refresh)

    Returns:
        JWT token
    """
    if expires_in is None:
        if token_type == "refresh":
            expires_in = current_app.config.get("REFRESH_TOKEN_EXPIRY_DAYS", 30) * 24 * 60 * 60
        else:
            expires_in = current_app.config.get("TOKEN_EXPIRY_HOURS", 24) * 60 * 60

    payload = {
        "user_id": user_id,
        "type": token_type,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        "iat": datetime.now(timezone.utc),
    }

    return jwt.encode(
        payload,
        current_app.config["SECRET_KEY"],
        algorithm="HS256",
    )


def verify_token(token: str) -> dict:
    """
    Verify a JWT token.

    Args:
        token: JWT token

    Returns:
        Token payload if valid

    Raises:
        jwt.InvalidTokenError: If token is invalid
    """
    return jwt.decode(
        token,
        current_app.config["SECRET_KEY"],
        algorithms=["HS256"],
    )


def generate_reset_token(user_id: str) -> str:
    """
    Generate a password reset token.

    Args:
        user_id: User ID

    Returns:
        Reset token
    """
    expires_in = current_app.config.get("RESET_TOKEN_EXPIRY_HOURS", 1) * 60 * 60
    return generate_token(user_id, expires_in, "reset")


def generate_verification_token(user_id: str) -> str:
    """
    Generate an email verification token.

    Args:
        user_id: User ID

    Returns:
        Verification token
    """
    expires_in = current_app.config.get("VERIFICATION_TOKEN_EXPIRY_HOURS", 24) * 60 * 60
    return generate_token(user_id, expires_in, "verification")


def generate_api_key() -> str:
    """
    Generate a secure API key.

    Returns:
        API key
    """
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for storage.

    Args:
        api_key: Plain text API key

    Returns:
        Hashed API key
    """
    return generate_password_hash(api_key)


def verify_api_key(api_key: str, api_key_hash: str) -> bool:
    """
    Verify an API key against its hash.

    Args:
        api_key: Plain text API key
        api_key_hash: Hashed API key

    Returns:
        True if API key matches, False otherwise
    """
    return verify_password(api_key, api_key_hash)


def generate_salt(length: Optional[int] = None) -> str:
    """
    Generate a random salt.

    Args:
        length: Length of salt in bytes

    Returns:
        Random salt
    """
    if length is None:
        length = current_app.config.get("PASSWORD_SALT_LENGTH", 16)
    return secrets.token_hex(length)


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """
    Hash a password with a salt.

    Args:
        password: Plain text password
        salt: Optional salt (if not provided, a new one will be generated)

    Returns:
        Tuple of (hashed password, salt)
    """
    if salt is None:
        salt = generate_salt()
    return generate_password_hash(password + salt), salt


def verify_password_with_salt(password: str, password_hash: str, salt: str) -> bool:
    """
    Verify a password against its hash and salt.

    Args:
        password: Plain text password
        password_hash: Hashed password
        salt: Salt used in hashing

    Returns:
        True if password matches, False otherwise
    """
    return verify_password(password + salt, password_hash)


def generate_csrf_token() -> str:
    """
    Generate a CSRF token.

    Returns:
        CSRF token
    """
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, stored_token: str) -> bool:
    """
    Verify a CSRF token.

    Args:
        token: Token to verify
        stored_token: Stored token to compare against

    Returns:
        True if tokens match, False otherwise
    """
    return secrets.compare_digest(token, stored_token)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove any path components
    filename = os.path.basename(filename)
    # Replace any non-alphanumeric characters with underscores
    filename = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
    return filename


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, message)
    """
    if len(password) < current_app.config.get("MIN_PASSWORD_LENGTH", 8):
        return False, "Password must be at least 8 characters long"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"

    if not any(c in '!@#$%^&*(),.?":{}|<>' for c in password):
        return False, "Password must contain at least one special character"

    return True, "Password is strong"
