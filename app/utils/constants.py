"""Constants used throughout the application."""

# API Response Status Codes
SUCCESS = "success"
ERROR = "error"
PENDING = "pending"
FAILED = "failed"

# HTTP Methods
GET = "GET"
POST = "POST"
PUT = "PUT"
DELETE = "DELETE"
PATCH = "PATCH"

# Common HTTP Headers
CONTENT_TYPE = "Content-Type"
AUTHORIZATION = "Authorization"
ACCEPT = "Accept"
USER_AGENT = "User-Agent"

# Content Types
JSON_CONTENT_TYPE = "application/json"
FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"
MULTIPART_CONTENT_TYPE = "multipart/form-data"

# Authentication Types
BEARER_AUTH = "Bearer"
BASIC_AUTH = "Basic"
API_KEY_AUTH = "ApiKey"

# Pagination Settings
DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 10
MAX_PER_PAGE = 100

# Sorting Options
DEFAULT_SORT_BY = "created_at"
DEFAULT_SORT_ORDER = "desc"
ASCENDING = "asc"
DESCENDING = "desc"

# File Upload Limits
MAX_FILE_SIZE_MB = 5
ALLOWED_FILE_EXTENSIONS = ["jpg", "jpeg", "png", "gif", "pdf"]
MAX_FILENAME_LENGTH = 255

# Search Parameters
DEFAULT_SEARCH_RADIUS_KM = 5
MAX_SEARCH_RADIUS_KM = 50
MIN_SEARCH_RADIUS_KM = 0.1

# Validation Rules
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 50
MIN_NAME_LENGTH = 2
MAX_NAME_LENGTH = 100
MIN_COMMENT_LENGTH = 1
MAX_COMMENT_LENGTH = 1000
MIN_TAG_LENGTH = 2
MAX_TAG_LENGTH = 50
MAX_TAGS = 10

# Cache Settings
CACHE_TIMEOUT = 300  # 5 minutes
CACHE_PREFIX = "app_cache:"
CACHE_KEY_SEPARATOR = ":"

# Rate Limiting
RATE_LIMIT_DEFAULT = "100 per minute"
RATE_LIMIT_STRICT = "10 per minute"
RATE_LIMIT_HEADERS = True

# Security
PASSWORD_SALT_LENGTH = 16
TOKEN_EXPIRY_HOURS = 24
REFRESH_TOKEN_EXPIRY_DAYS = 30
MAX_LOGIN_ATTEMPTS = 5
LOGIN_TIMEOUT_MINUTES = 15

# Email Settings
EMAIL_FROM = "noreply@example.com"
EMAIL_SUBJECT_PREFIX = "[App] "
EMAIL_TEMPLATE_DIR = "templates/email"

# SMS Settings
SMS_FROM = "+1234567890"
SMS_TEMPLATE_DIR = "templates/sms"

# Database Connection Settings
DB_POOL_SIZE = 5
DB_MAX_OVERFLOW = 10
DB_POOL_TIMEOUT = 30
DB_POOL_RECYCLE = 1800

# Logging Configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_LEVEL = "INFO"
LOG_FILE = "app.log"

# Error Messages
ERROR_MESSAGES = {
    "invalid_input": "Invalid input provided",
    "missing_field": "Required field is missing",
    "invalid_field": "Invalid field value",
    "duplicate_field": "Field value already exists",
    "not_found": "Resource not found",
    "unauthorized": "Unauthorized access",
    "forbidden": "Access forbidden",
    "server_error": "Internal server error",
    "validation_error": "Validation error",
    "rate_limit": "Rate limit exceeded",
    "invalid_token": "Invalid or expired token",
    "invalid_credentials": "Invalid credentials",
    "account_locked": "Account is locked",
    "email_verification": "Email verification required",
    "phone_verification": "Phone verification required",
    "file_upload": "File upload failed",
    "file_size": "File size exceeds limit",
    "file_type": "Invalid file type",
    "search_error": "Search operation failed",
    "geocoding_error": "Geocoding operation failed",
    "booking_error": "Booking operation failed",
    "payment_error": "Payment processing failed",
    "notification_error": "Notification sending failed",
    "cache_error": "Cache operation failed",
    "database_error": "Database operation failed",
    "external_api_error": "External API error",
    "timeout_error": "Operation timed out",
    "network_error": "Network connection error",
    "maintenance_mode": "System is under maintenance",
    "service_unavailable": "Service temporarily unavailable",
    "bad_gateway": "Bad gateway",
    "gateway_timeout": "Gateway timeout",
    "too_many_requests": "Too many requests",
    "request_entity_too_large": "Request entity too large",
    "unsupported_media_type": "Unsupported media type",
    "not_acceptable": "Not acceptable",
    "conflict": "Resource conflict",
    "gone": "Resource is gone",
    "precondition_failed": "Precondition failed",
    "unprocessable_entity": "Unprocessable entity",
    "locked": "Resource is locked",
    "failed_dependency": "Failed dependency",
    "upgrade_required": "Upgrade required",
    "precondition_required": "Precondition required",
    "too_many_connections": "Too many connections",
    "legal_reasons": "Unavailable for legal reasons",
    "internal_server_error": "Internal server error",
    "not_implemented": "Not implemented",
    "http_version_not_supported": "HTTP version not supported",
    "variant_also_negotiates": "Variant also negotiates",
    "insufficient_storage": "Insufficient storage",
    "loop_detected": "Loop detected",
    "not_extended": "Not extended",
    "network_authentication_required": "Network authentication required",
}
