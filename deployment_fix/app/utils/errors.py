"""Custom error classes for the application."""

from typing import Any, Dict, Optional

from werkzeug.exceptions import HTTPException


class AppError(HTTPException):
    """Base class for application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the error.

        Args:
            message: Error message
            status_code: HTTP status code
            details: Additional error details
        """
        super().__init__(description=message)
        self.code = status_code
        self.details = details or {}


class ValidationError(AppError):
    """Error raised when validation fails."""

    def __init__(
        self,
        message: str = "Validation error",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the validation error.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, 400, details)


class AuthenticationError(AppError):
    """Error raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the authentication error.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, 401, details)


class AuthorizationError(AppError):
    """Error raised when authorization fails."""

    def __init__(
        self,
        message: str = "Authorization failed",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the authorization error.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, 403, details)


class NotFoundError(AppError):
    """Error raised when a resource is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the not found error.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, 404, details)


class ConflictError(AppError):
    """Error raised when a resource conflict occurs."""

    def __init__(
        self,
        message: str = "Resource conflict",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the conflict error.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, 409, details)


class RateLimitError(AppError):
    """Error raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the rate limit error.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, 429, details)


class ExternalAPIError(AppError):
    """Error raised when external API calls fail."""

    def __init__(
        self,
        message: str = "External API error",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the external API error.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, 502, details)


class DatabaseError(AppError):
    """Error raised when database operations fail."""

    def __init__(
        self,
        message: str = "Database error",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the database error.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, 500, details)


class CacheError(AppError):
    """Error raised when cache operations fail."""

    def __init__(
        self,
        message: str = "Cache error",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the cache error.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, 500, details)


class NotificationError(AppError):
    """Error raised when notification sending fails."""

    def __init__(
        self,
        message: str = "Notification error",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the notification error.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, 500, details)


class FileUploadError(AppError):
    """Error raised when file upload fails."""

    def __init__(
        self,
        message: str = "File upload error",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the file upload error.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, 400, details)


class SearchError(AppError):
    """Error raised when search operations fail."""

    def __init__(
        self,
        message: str = "Search error",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the search error.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, 500, details)


class GeocodingError(AppError):
    """Error raised when geocoding operations fail."""

    def __init__(
        self,
        message: str = "Geocoding error",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the geocoding error.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, 500, details)


class BookingError(AppError):
    """Error raised when booking operations fail."""

    def __init__(
        self,
        message: str = "Booking error",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the booking error.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, 400, details)


class PaymentError(AppError):
    """Error raised when payment operations fail."""

    def __init__(
        self,
        message: str = "Payment error",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the payment error.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message, 400, details)
