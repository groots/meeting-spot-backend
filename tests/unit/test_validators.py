from datetime import datetime
from typing import Dict, List
from unittest.mock import MagicMock, patch

import pytest

from app.utils import validators


def test_validate_email():
    """Test email validation"""
    # Valid emails
    assert validators.validate_email("user@example.com") is True
    assert validators.validate_email("test.user@example.co.uk") is True
    assert validators.validate_email("test-user_123@sub.example.org") is True

    # Invalid emails
    assert validators.validate_email("") is False
    assert validators.validate_email("user@") is False
    assert validators.validate_email("user@.com") is False
    assert validators.validate_email("@example.com") is False
    assert validators.validate_email("user@example") is False
    assert validators.validate_email("user example.com") is False


def test_validate_phone_number():
    """Test phone number validation"""
    # Valid phone numbers
    assert validators.validate_phone_number("1234567890") is True
    assert validators.validate_phone_number("+1-234-567-8900") is True
    assert validators.validate_phone_number("(123) 456-7890") is True

    # Invalid phone numbers
    assert validators.validate_phone_number("") is False
    assert validators.validate_phone_number("123") is False
    assert validators.validate_phone_number("abcdefghij") is False
    assert validators.validate_phone_number("12345678901234567890") is False


def test_validate_password():
    """Test password validation"""
    # Valid passwords
    assert validators.validate_password("Password123!") is True
    assert validators.validate_password("StrongP@ssw0rd") is True
    assert validators.validate_password("C0mplex!Pass") is True

    # Invalid passwords - too short
    assert validators.validate_password("Pass1!") is False

    # Invalid passwords - no uppercase
    assert validators.validate_password("password123!") is False

    # Invalid passwords - no lowercase
    assert validators.validate_password("PASSWORD123!") is False

    # Invalid passwords - no number
    assert validators.validate_password("Password!") is False

    # Invalid passwords - no special character
    assert validators.validate_password("Password123") is False


def test_validate_date():
    """Test date validation"""
    # Valid dates
    assert validators.validate_date("2023-01-01") is True
    assert validators.validate_date("2024-02-29") is True  # Leap year
    assert validators.validate_date("2022-12-31") is True

    # Invalid dates
    assert validators.validate_date("") is False
    assert validators.validate_date("01-01-2023") is False  # Wrong format
    assert validators.validate_date("2023-13-01") is False  # Invalid month
    assert validators.validate_date("2023-01-32") is False  # Invalid day
    assert validators.validate_date("2023-02-29") is False  # Not a leap year


def test_validate_time():
    """Test time validation"""
    # Valid times
    assert validators.validate_time("12:30") is True
    assert validators.validate_time("00:00") is True
    assert validators.validate_time("23:59") is True

    # Invalid times
    assert validators.validate_time("") is False
    assert validators.validate_time("12:60") is False  # Invalid minute
    assert validators.validate_time("24:00") is False  # Invalid hour
    assert validators.validate_time("12:30 AM") is False  # Wrong format
    assert validators.validate_time("12:30:00") is False  # Includes seconds


def test_validate_datetime():
    """Test datetime validation"""
    # Valid datetimes
    assert validators.validate_datetime("2023-01-01 12:30") is True
    assert validators.validate_datetime("2022-12-31 23:59") is True

    # Invalid datetimes
    assert validators.validate_datetime("") is False
    assert validators.validate_datetime("2023-01-01") is False  # Missing time
    assert validators.validate_datetime("12:30") is False  # Missing date
    assert validators.validate_datetime("01-01-2023 12:30") is False  # Wrong date format
    assert validators.validate_datetime("2023-01-01 12:30:00") is False  # Includes seconds


def test_validate_coordinates():
    """Test coordinate validation"""
    # Valid coordinates
    assert validators.validate_coordinates(0, 0) is True
    assert validators.validate_coordinates(90, 180) is True
    assert validators.validate_coordinates(-90, -180) is True
    assert validators.validate_coordinates(45.12345, -120.67890) is True

    # Invalid coordinates
    assert validators.validate_coordinates(91, 0) is False  # Latitude too high
    assert validators.validate_coordinates(-91, 0) is False  # Latitude too low
    assert validators.validate_coordinates(0, 181) is False  # Longitude too high
    assert validators.validate_coordinates(0, -181) is False  # Longitude too low


@patch("app.utils.validators.current_app")
def test_validate_radius(mock_current_app):
    """Test radius validation"""
    # Setup mock
    mock_config = MagicMock()
    mock_config.get.return_value = 50
    mock_current_app.config = mock_config

    # Valid radius
    assert validators.validate_radius(1) is True
    assert validators.validate_radius(25) is True
    assert validators.validate_radius(50) is True

    # Invalid radius
    assert validators.validate_radius(0) is False  # Must be positive
    assert validators.validate_radius(-5) is False  # Negative value
    assert validators.validate_radius(51) is False  # Exceeds max

    # Check the mock was called correctly
    mock_config.get.assert_called_with("MAX_SEARCH_RADIUS", 50)


def test_validate_name():
    """Test name validation"""
    # Valid names
    assert validators.validate_name("John") is True
    assert validators.validate_name("Mary Smith") is True
    assert validators.validate_name("Jean-Claude") is True
    assert validators.validate_name("O'Connor") is True

    # Invalid names
    assert validators.validate_name("") is False  # Empty string
    assert validators.validate_name("A") is False  # Too short
    assert validators.validate_name("John123") is False  # Contains numbers
    assert validators.validate_name("John!") is False  # Contains invalid special characters


def test_validate_username():
    """Test username validation"""
    # Valid usernames
    assert validators.validate_username("john") is True
    assert validators.validate_username("john_doe") is True
    assert validators.validate_username("john123") is True

    # Invalid usernames
    assert validators.validate_username("") is False  # Empty string
    assert validators.validate_username("jo") is False  # Too short
    assert validators.validate_username("john-doe") is False  # Contains hyphen
    assert validators.validate_username("john doe") is False  # Contains space
    assert validators.validate_username("john!") is False  # Contains special characters


def test_validate_url():
    """Test URL validation"""
    # Valid URLs
    assert validators.validate_url("http://example.com") is True
    assert validators.validate_url("https://example.com") is True
    assert validators.validate_url("http://example.com/path") is True
    assert validators.validate_url("https://example.com/path?query=value") is True

    # Invalid URLs
    assert validators.validate_url("") is False  # Empty string
    assert validators.validate_url("example.com") is False  # Missing protocol
    assert validators.validate_url("htp://example.com") is False  # Invalid protocol
    assert validators.validate_url("http:/example.com") is False  # Missing slash


def test_validate_file_extension():
    """Test file extension validation"""
    allowed_extensions = ["jpg", "png", "pdf"]

    # Valid file extensions
    assert validators.validate_file_extension("document.pdf", allowed_extensions) is True
    assert validators.validate_file_extension("image.jpg", allowed_extensions) is True
    assert validators.validate_file_extension("photo.png", allowed_extensions) is True
    assert validators.validate_file_extension("file.name.with.dots.jpg", allowed_extensions) is True

    # Invalid file extensions
    assert validators.validate_file_extension("document", allowed_extensions) is False  # No extension
    assert validators.validate_file_extension("document.docx", allowed_extensions) is False  # Not allowed
    assert (
        validators.validate_file_extension(".pdf", allowed_extensions) is True
    )  # Actually valid as "pdf" is extracted
    assert validators.validate_file_extension("document.PDF", allowed_extensions) is True  # Case insensitive


def test_validate_file_size():
    """Test file size validation"""
    # Default max size (5MB)
    assert validators.validate_file_size(1024) is True  # 1KB
    assert validators.validate_file_size(1024 * 1024) is True  # 1MB
    assert validators.validate_file_size(5 * 1024 * 1024) is True  # 5MB
    assert validators.validate_file_size(6 * 1024 * 1024) is False  # 6MB

    # Custom max size (10MB)
    assert validators.validate_file_size(8 * 1024 * 1024, 10) is True  # 8MB
    assert validators.validate_file_size(10 * 1024 * 1024, 10) is True  # 10MB
    assert validators.validate_file_size(11 * 1024 * 1024, 10) is False  # 11MB


def test_validate_rating():
    """Test rating validation"""
    # Valid ratings
    assert validators.validate_rating(0) is True
    assert validators.validate_rating(2.5) is True
    assert validators.validate_rating(5) is True

    # Invalid ratings
    assert validators.validate_rating(-1) is False  # Negative
    assert validators.validate_rating(6) is False  # Too high


def test_validate_comment_length():
    """Test comment length validation"""
    # Valid comments (default max length 1000)
    assert validators.validate_comment_length("") is True  # Empty is valid
    assert validators.validate_comment_length("Short comment") is True
    assert validators.validate_comment_length("A" * 1000) is True  # Exactly max length

    # Invalid comments
    assert validators.validate_comment_length("A" * 1001) is False  # Too long

    # Custom max length
    assert validators.validate_comment_length("A" * 500, 500) is True  # Exactly max length
    assert validators.validate_comment_length("A" * 501, 500) is False  # Too long


def test_validate_tags():
    """Test tags validation"""
    # Valid tags
    assert validators.validate_tags(["tag1", "tag2"]) is True
    assert validators.validate_tags(["abc123", "hello world"]) is True

    # Invalid tags
    assert validators.validate_tags([]) is False  # Empty list
    assert validators.validate_tags(["a"]) is False  # Tag too short
    assert validators.validate_tags(["tag1", "invalid-tag"]) is False  # Contains invalid character
    assert validators.validate_tags(["tag1", "tag!"]) is False  # Contains invalid character


def test_validate_price_range():
    """Test price range validation"""
    # Valid price ranges
    assert validators.validate_price_range(0, 0) is True  # Both zero
    assert validators.validate_price_range(10, 20) is True  # Min less than max
    assert validators.validate_price_range(50, 50) is True  # Equal values

    # Invalid price ranges
    assert validators.validate_price_range(-10, 20) is False  # Negative min
    assert validators.validate_price_range(20, 10) is False  # Min greater than max


def test_validate_capacity():
    """Test capacity validation"""
    # Valid capacities
    assert validators.validate_capacity(1) is True
    assert validators.validate_capacity(100) is True

    # Invalid capacities
    assert validators.validate_capacity(0) is False  # Zero
    assert validators.validate_capacity(-5) is False  # Negative


def test_validate_duration():
    """Test duration validation"""
    # Valid durations
    assert validators.validate_duration(1) is True  # 1 minute
    assert validators.validate_duration(60) is True  # 1 hour
    assert validators.validate_duration(480) is True  # 8 hours

    # Invalid durations
    assert validators.validate_duration(0) is False  # Zero
    assert validators.validate_duration(-30) is False  # Negative
    assert validators.validate_duration(481) is False  # Exceeds max


def test_validate_availability():
    """Test availability validation"""
    # Sample existing bookings
    existing_bookings = [
        {"start_time": "2023-01-01 10:00", "end_time": "2023-01-01 12:00"},
        {"start_time": "2023-01-01 14:00", "end_time": "2023-01-01 16:00"},
    ]

    # Valid time slots (no overlap)
    assert validators.validate_availability("2023-01-01 08:00", "2023-01-01 09:30", existing_bookings) is True
    assert validators.validate_availability("2023-01-01 12:30", "2023-01-01 13:30", existing_bookings) is True
    assert validators.validate_availability("2023-01-01 16:30", "2023-01-01 18:00", existing_bookings) is True

    # Invalid time slots (overlap)
    assert validators.validate_availability("2023-01-01 09:00", "2023-01-01 10:30", existing_bookings) is False
    assert validators.validate_availability("2023-01-01 11:00", "2023-01-01 13:00", existing_bookings) is False
    assert validators.validate_availability("2023-01-01 11:00", "2023-01-01 15:00", existing_bookings) is False
    assert validators.validate_availability("2023-01-01 09:00", "2023-01-01 17:00", existing_bookings) is False

    # Invalid date/time format
    assert validators.validate_availability("invalid", "2023-01-01 12:00", existing_bookings) is False
    assert validators.validate_availability("2023-01-01 10:00", "invalid", existing_bookings) is False


@patch("app.utils.validators.current_app")
def test_validate_pagination_params(mock_current_app):
    """Test pagination parameters validation"""
    # Valid pagination parameters
    assert validators.validate_pagination_params(1, 10)[0] is True
    assert validators.validate_pagination_params(100, 100)[0] is True

    # Invalid pagination parameters
    assert validators.validate_pagination_params(0, 10)[0] is False
    assert validators.validate_pagination_params(-1, 10)[0] is False
    assert validators.validate_pagination_params(1, 0)[0] is False
    assert validators.validate_pagination_params(1, -10)[0] is False
    assert validators.validate_pagination_params(1, 101)[0] is False

    # Check with custom max_per_page
    assert validators.validate_pagination_params(1, 20, 20)[0] is True
    assert validators.validate_pagination_params(1, 21, 20)[0] is False
