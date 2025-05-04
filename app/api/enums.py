"""Enumeration types and constants for the API.

This module provides various enumeration types and constants used throughout the API.
"""

from enum import Enum, auto


class HttpMethod(str, Enum):
    """HTTP method enumeration."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"
    HEAD = "HEAD"


class ContentType(str, Enum):
    """Content type enumeration."""

    JSON = "application/json"
    FORM = "application/x-www-form-urlencoded"
    MULTIPART = "multipart/form-data"
    TEXT = "text/plain"
    HTML = "text/html"
    XML = "application/xml"


class AuthType(str, Enum):
    """Authentication type enumeration."""

    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    JWT = "jwt"
    API_KEY = "api_key"


class SortOrder(str, Enum):
    """Sort order enumeration."""

    ASC = "asc"
    DESC = "desc"


class FileType(str, Enum):
    """File type enumeration."""

    IMAGE = "image"
    DOCUMENT = "document"
    VIDEO = "video"
    AUDIO = "audio"
    OTHER = "other"


class ErrorType(str, Enum):
    """Error type enumeration."""

    VALIDATION = "validation_error"
    AUTHENTICATION = "authentication_error"
    AUTHORIZATION = "authorization_error"
    NOT_FOUND = "not_found_error"
    CONFLICT = "conflict_error"
    RATE_LIMIT = "rate_limit_error"
    EXTERNAL_API = "external_api_error"
    DATABASE = "database_error"
    CACHE = "cache_error"
    NOTIFICATION = "notification_error"
    FILE_UPLOAD = "file_upload_error"
    SEARCH = "search_error"
    GEOCODING = "geocoding_error"
    BOOKING = "booking_error"
    PAYMENT = "payment_error"
    SERVER = "server_error"


class MeetingCategory(str, Enum):
    """Meeting category enumeration."""

    COFFEE = "coffee"
    RESTAURANT = "restaurant"
    BAR = "bar"
    PARK = "park"
    LIBRARY = "library"
    COWORKING = "coworking"
    OTHER = "other"


class MeetingStatus(str, Enum):
    """Meeting request status enumeration."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELED = "canceled"
    COMPLETED = "completed"


# Constants for pagination
DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100

# Constants for search
DEFAULT_SEARCH_RADIUS = 5000  # meters
MAX_SEARCH_RADIUS = 50000  # meters

# Constants for validation
MIN_PASSWORD_LENGTH = 8
MAX_USERNAME_LENGTH = 30
MAX_NAME_LENGTH = 100
MAX_COMMENT_LENGTH = 500
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Constants for rate limiting
RATE_LIMIT_DEFAULT = 60  # requests per minute
RATE_LIMIT_AUTH = 10  # auth requests per minute

# Constants for caching
DEFAULT_CACHE_TIMEOUT = 300  # 5 minutes
