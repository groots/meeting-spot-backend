import pytest

from app.utils import errors


def test_app_error():
    """Test the base AppError class"""
    # Test with default parameters
    error = errors.AppError("Test error")
    assert error.description == "Test error"
    assert error.code == 400
    assert error.details == {}

    # Test with custom parameters
    error = errors.AppError("Custom error", 422, {"field": "value"})
    assert error.description == "Custom error"
    assert error.code == 422
    assert error.details == {"field": "value"}


def test_validation_error():
    """Test ValidationError class"""
    # Test with default parameters
    error = errors.ValidationError()
    assert error.description == "Validation error"
    assert error.code == 400
    assert error.details == {}

    # Test with custom parameters
    error = errors.ValidationError("Invalid input", {"field": "This field is required"})
    assert error.description == "Invalid input"
    assert error.code == 400
    assert error.details == {"field": "This field is required"}


def test_authentication_error():
    """Test AuthenticationError class"""
    # Test with default parameters
    error = errors.AuthenticationError()
    assert error.description == "Authentication failed"
    assert error.code == 401
    assert error.details == {}

    # Test with custom parameters
    error = errors.AuthenticationError("Invalid token", {"token": "expired"})
    assert error.description == "Invalid token"
    assert error.code == 401
    assert error.details == {"token": "expired"}


def test_authorization_error():
    """Test AuthorizationError class"""
    # Test with default parameters
    error = errors.AuthorizationError()
    assert error.description == "Authorization failed"
    assert error.code == 403
    assert error.details == {}

    # Test with custom parameters
    error = errors.AuthorizationError("Insufficient permissions", {"required": "admin"})
    assert error.description == "Insufficient permissions"
    assert error.code == 403
    assert error.details == {"required": "admin"}


def test_not_found_error():
    """Test NotFoundError class"""
    # Test with default parameters
    error = errors.NotFoundError()
    assert error.description == "Resource not found"
    assert error.code == 404
    assert error.details == {}

    # Test with custom parameters
    error = errors.NotFoundError("User not found", {"user_id": 123})
    assert error.description == "User not found"
    assert error.code == 404
    assert error.details == {"user_id": 123}


def test_conflict_error():
    """Test ConflictError class"""
    # Test with default parameters
    error = errors.ConflictError()
    assert error.description == "Resource conflict"
    assert error.code == 409
    assert error.details == {}

    # Test with custom parameters
    error = errors.ConflictError("User already exists", {"email": "user@example.com"})
    assert error.description == "User already exists"
    assert error.code == 409
    assert error.details == {"email": "user@example.com"}


def test_rate_limit_error():
    """Test RateLimitError class"""
    # Test with default parameters
    error = errors.RateLimitError()
    assert error.description == "Rate limit exceeded"
    assert error.code == 429
    assert error.details == {}

    # Test with custom parameters
    error = errors.RateLimitError("Too many requests", {"retry_after": 60})
    assert error.description == "Too many requests"
    assert error.code == 429
    assert error.details == {"retry_after": 60}


def test_external_api_error():
    """Test ExternalAPIError class"""
    # Test with default parameters
    error = errors.ExternalAPIError()
    assert error.description == "External API error"
    assert error.code == 502
    assert error.details == {}

    # Test with custom parameters
    error = errors.ExternalAPIError("Google API error", {"status": "INVALID_REQUEST"})
    assert error.description == "Google API error"
    assert error.code == 502
    assert error.details == {"status": "INVALID_REQUEST"}


def test_database_error():
    """Test DatabaseError class"""
    # Test with default parameters
    error = errors.DatabaseError()
    assert error.description == "Database error"
    assert error.code == 500
    assert error.details == {}

    # Test with custom parameters
    error = errors.DatabaseError("Connection failed", {"error": "timeout"})
    assert error.description == "Connection failed"
    assert error.code == 500
    assert error.details == {"error": "timeout"}


def test_cache_error():
    """Test CacheError class"""
    # Test with default parameters
    error = errors.CacheError()
    assert error.description == "Cache error"
    assert error.code == 500
    assert error.details == {}

    # Test with custom parameters
    error = errors.CacheError("Redis connection error", {"error": "connection refused"})
    assert error.description == "Redis connection error"
    assert error.code == 500
    assert error.details == {"error": "connection refused"}


def test_notification_error():
    """Test NotificationError class"""
    # Test with default parameters
    error = errors.NotificationError()
    assert error.description == "Notification error"
    assert error.code == 500
    assert error.details == {}

    # Test with custom parameters
    error = errors.NotificationError("Email sending failed", {"recipient": "user@example.com"})
    assert error.description == "Email sending failed"
    assert error.code == 500
    assert error.details == {"recipient": "user@example.com"}


def test_file_upload_error():
    """Test FileUploadError class"""
    # Test with default parameters
    error = errors.FileUploadError()
    assert error.description == "File upload error"
    assert error.code == 400
    assert error.details == {}

    # Test with custom parameters
    error = errors.FileUploadError("File too large", {"max_size": "5MB"})
    assert error.description == "File too large"
    assert error.code == 400
    assert error.details == {"max_size": "5MB"}


def test_search_error():
    """Test SearchError class"""
    # Test with default parameters
    error = errors.SearchError()
    assert error.description == "Search error"
    assert error.code == 500
    assert error.details == {}

    # Test with custom parameters
    error = errors.SearchError("Index not found", {"index": "users"})
    assert error.description == "Index not found"
    assert error.code == 500
    assert error.details == {"index": "users"}


def test_geocoding_error():
    """Test GeocodingError class"""
    # Test with default parameters
    error = errors.GeocodingError()
    assert error.description == "Geocoding error"
    assert error.code == 500
    assert error.details == {}

    # Test with custom parameters
    error = errors.GeocodingError("Invalid address", {"address": "123 Nowhere"})
    assert error.description == "Invalid address"
    assert error.code == 500
    assert error.details == {"address": "123 Nowhere"}


def test_booking_error():
    """Test BookingError class"""
    # Test with default parameters
    error = errors.BookingError()
    assert error.description == "Booking error"
    assert error.code == 400
    assert error.details == {}

    # Test with custom parameters
    error = errors.BookingError("Slot already booked", {"time": "2023-01-01 12:00"})
    assert error.description == "Slot already booked"
    assert error.code == 400
    assert error.details == {"time": "2023-01-01 12:00"}


def test_payment_error():
    """Test PaymentError class"""
    # Test with default parameters
    error = errors.PaymentError()
    assert error.description == "Payment error"
    assert error.code == 400
    assert error.details == {}

    # Test with custom parameters
    error = errors.PaymentError("Payment declined", {"reason": "insufficient funds"})
    assert error.description == "Payment declined"
    assert error.code == 400
    assert error.details == {"reason": "insufficient funds"}
