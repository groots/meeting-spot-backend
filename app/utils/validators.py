"""Validation utilities for the application."""

import re
from datetime import datetime
from typing import Optional

from flask import current_app


def validate_email(email: str) -> bool:
    """
    Validate an email address.
    Returns True if valid, False otherwise.
    """
    # Basic email regex pattern
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_phone_number(phone: str) -> bool:
    """
    Validate a phone number.
    Returns True if valid, False otherwise.
    """
    # Remove any non-digit characters
    digits = re.sub(r"\D", "", phone)
    return len(digits) >= 10 and len(digits) <= 15


def validate_password(password: str) -> bool:
    """
    Validate a password.
    Returns True if valid, False otherwise.
    """
    # Password must be at least 8 characters long
    if len(password) < 8:
        return False

    # Password must contain at least one uppercase letter
    if not re.search(r"[A-Z]", password):
        return False

    # Password must contain at least one lowercase letter
    if not re.search(r"[a-z]", password):
        return False

    # Password must contain at least one number
    if not re.search(r"\d", password):
        return False

    # Password must contain at least one special character
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False

    return True


def validate_date(date_str: str) -> bool:
    """
    Validate a date string.
    Returns True if valid, False otherwise.
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_time(time_str: str) -> bool:
    """
    Validate a time string.
    Returns True if valid, False otherwise.
    """
    try:
        datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False


def validate_datetime(datetime_str: str) -> bool:
    """
    Validate a datetime string.
    Returns True if valid, False otherwise.
    """
    try:
        datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        return True
    except ValueError:
        return False


def validate_coordinates(lat: float, lon: float) -> bool:
    """
    Validate latitude and longitude coordinates.
    Returns True if valid, False otherwise.
    """
    return -90 <= lat <= 90 and -180 <= lon <= 180


def validate_radius(radius: float) -> bool:
    """
    Validate a search radius in kilometers.
    Returns True if valid, False otherwise.
    """
    max_radius = current_app.config.get("MAX_SEARCH_RADIUS", 50)
    return 0 < radius <= max_radius


def validate_name(name: str) -> bool:
    """
    Validate a name string.
    Returns True if valid, False otherwise.
    """
    # Name must be at least 2 characters long
    if len(name) < 2:
        return False

    # Name must contain only letters, spaces, and basic punctuation
    pattern = r"^[a-zA-Z\s\-']+$"
    return bool(re.match(pattern, name))


def validate_username(username: str) -> bool:
    """
    Validate a username string.
    Returns True if valid, False otherwise.
    """
    # Username must be at least 3 characters long
    if len(username) < 3:
        return False

    # Username must contain only letters, numbers, and underscores
    pattern = r"^[a-zA-Z0-9_]+$"
    return bool(re.match(pattern, username))


def validate_url(url: str) -> bool:
    """
    Validate a URL string.
    Returns True if valid, False otherwise.
    """
    pattern = r"^https?://(?:[\w-]|(?=%[\da-fA-F]{2}))+[^\s]*$"
    return bool(re.match(pattern, url))


def validate_file_extension(filename: str, allowed_extensions: list[str]) -> bool:
    """
    Validate a file extension.
    Returns True if valid, False otherwise.
    """
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def validate_file_size(file_size: int, max_size_mb: int = 5) -> bool:
    """
    Validate a file size.
    Returns True if valid, False otherwise.
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    return file_size <= max_size_bytes


def validate_rating(rating: float) -> bool:
    """
    Validate a rating value.
    Returns True if valid, False otherwise.
    """
    return 0 <= rating <= 5


def validate_comment_length(comment: str, max_length: int = 1000) -> bool:
    """
    Validate a comment length.
    Returns True if valid, False otherwise.
    """
    return len(comment) <= max_length


def validate_tags(tags: list[str]) -> bool:
    """
    Validate a list of tags.
    Returns True if valid, False otherwise.
    """
    if not tags:
        return False

    # Each tag must be at least 2 characters long
    for tag in tags:
        if len(tag) < 2:
            return False

        # Tags must contain only letters, numbers, and spaces
        pattern = r"^[a-zA-Z0-9\s]+$"
        if not re.match(pattern, tag):
            return False

    return True


def validate_price_range(min_price: float, max_price: float) -> bool:
    """
    Validate a price range.
    Returns True if valid, False otherwise.
    """
    return 0 <= min_price <= max_price


def validate_capacity(capacity: int) -> bool:
    """
    Validate a capacity value.
    Returns True if valid, False otherwise.
    """
    return capacity > 0


def validate_duration(duration: int) -> bool:
    """
    Validate a duration in minutes.
    Returns True if valid, False otherwise.
    """
    return 0 < duration <= 480  # Max 8 hours


def validate_availability(start_time: str, end_time: str, existing_bookings: list[dict]) -> bool:
    """
    Validate if a time slot is available.
    Returns True if available, False otherwise.
    """
    try:
        new_start = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
        new_end = datetime.strptime(end_time, "%Y-%m-%d %H:%M")

        for booking in existing_bookings:
            existing_start = datetime.strptime(booking["start_time"], "%Y-%m-%d %H:%M")
            existing_end = datetime.strptime(booking["end_time"], "%Y-%m-%d %H:%M")

            # Check for overlap
            if new_start < existing_end and new_end > existing_start:
                return False

        return True
    except ValueError:
        return False


def validate_pagination_params(
    page: int, per_page: int, max_per_page: int = 100
) -> tuple[bool, Optional[str]]:
    """
    Validate pagination parameters.
    Returns a tuple of (is_valid, error_message).
    """
    if page < 1:
        return False, "Page number must be greater than 0"

    if per_page < 1:
        return False, "Items per page must be greater than 0"

    if per_page > max_per_page:
        return False, f"Items per page cannot exceed {max_per_page}"

    return True, None
