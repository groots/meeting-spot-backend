import pytest

from app.utils import constants


def test_constants_exist():
    """Test that important constants are defined"""
    # API Response Status Codes
    assert constants.SUCCESS == "success"
    assert constants.ERROR == "error"
    assert constants.PENDING == "pending"
    assert constants.FAILED == "failed"

    # HTTP Methods
    assert constants.GET == "GET"
    assert constants.POST == "POST"
    assert constants.PUT == "PUT"
    assert constants.DELETE == "DELETE"
    assert constants.PATCH == "PATCH"

    # Common HTTP Headers
    assert constants.CONTENT_TYPE == "Content-Type"
    assert constants.AUTHORIZATION == "Authorization"
    assert constants.ACCEPT == "Accept"
    assert constants.USER_AGENT == "User-Agent"


def test_content_type_constants():
    """Test content type constants"""
    assert constants.JSON_CONTENT_TYPE == "application/json"
    assert constants.FORM_CONTENT_TYPE == "application/x-www-form-urlencoded"
    assert constants.MULTIPART_CONTENT_TYPE == "multipart/form-data"


def test_authentication_constants():
    """Test authentication type constants"""
    assert constants.BEARER_AUTH == "Bearer"
    assert constants.BASIC_AUTH == "Basic"
    assert constants.API_KEY_AUTH == "ApiKey"


def test_pagination_constants():
    """Test pagination constants"""
    assert constants.DEFAULT_PAGE == 1
    assert constants.DEFAULT_PER_PAGE == 10
    assert constants.MAX_PER_PAGE == 100


def test_sorting_constants():
    """Test sorting constants"""
    assert constants.DEFAULT_SORT_BY == "created_at"
    assert constants.DEFAULT_SORT_ORDER == "desc"
    assert constants.ASCENDING == "asc"
    assert constants.DESCENDING == "desc"


def test_file_upload_constants():
    """Test file upload constants"""
    assert constants.MAX_FILE_SIZE_MB == 5
    assert isinstance(constants.ALLOWED_FILE_EXTENSIONS, list)
    assert len(constants.ALLOWED_FILE_EXTENSIONS) > 0
    assert "jpg" in constants.ALLOWED_FILE_EXTENSIONS
    assert constants.MAX_FILENAME_LENGTH == 255


def test_search_parameters():
    """Test search parameter constants"""
    assert constants.DEFAULT_SEARCH_RADIUS_KM == 5
    assert constants.MAX_SEARCH_RADIUS_KM == 50
    assert constants.MIN_SEARCH_RADIUS_KM == 0.1


def test_validation_rules():
    """Test validation rule constants"""
    assert constants.MIN_PASSWORD_LENGTH == 8
    assert constants.MAX_PASSWORD_LENGTH == 128
    assert constants.MIN_USERNAME_LENGTH == 3
    assert constants.MAX_USERNAME_LENGTH == 50
    assert constants.MIN_NAME_LENGTH == 2
    assert constants.MAX_NAME_LENGTH == 100
    assert constants.MIN_COMMENT_LENGTH == 1
    assert constants.MAX_COMMENT_LENGTH == 1000
    assert constants.MIN_TAG_LENGTH == 2
    assert constants.MAX_TAG_LENGTH == 50
    assert constants.MAX_TAGS == 10


def test_cache_settings():
    """Test cache setting constants"""
    assert constants.CACHE_TIMEOUT == 300
    assert constants.CACHE_PREFIX == "app_cache:"
    assert constants.CACHE_KEY_SEPARATOR == ":"


def test_rate_limiting_constants():
    """Test rate limiting constants"""
    assert constants.RATE_LIMIT_DEFAULT == "100 per minute"
    assert constants.RATE_LIMIT_STRICT == "10 per minute"
    assert constants.RATE_LIMIT_HEADERS is True


def test_security_constants():
    """Test security constants"""
    assert constants.PASSWORD_SALT_LENGTH == 16
    assert constants.TOKEN_EXPIRY_HOURS == 24
    assert constants.REFRESH_TOKEN_EXPIRY_DAYS == 30
    assert constants.MAX_LOGIN_ATTEMPTS == 5
    assert constants.LOGIN_TIMEOUT_MINUTES == 15


def test_email_settings():
    """Test email setting constants"""
    assert constants.EMAIL_FROM == "noreply@example.com"
    assert constants.EMAIL_SUBJECT_PREFIX == "[App] "
    assert constants.EMAIL_TEMPLATE_DIR == "templates/email"


def test_sms_settings():
    """Test SMS setting constants"""
    assert constants.SMS_FROM == "+1234567890"
    assert constants.SMS_TEMPLATE_DIR == "templates/sms"


def test_database_connection_settings():
    """Test database connection constants"""
    assert constants.DB_POOL_SIZE == 5
    assert constants.DB_MAX_OVERFLOW == 10
    assert constants.DB_POOL_TIMEOUT == 30
    assert constants.DB_POOL_RECYCLE == 1800


def test_logging_configuration():
    """Test logging configuration constants"""
    assert constants.LOG_FORMAT == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    assert constants.LOG_DATE_FORMAT == "%Y-%m-%d %H:%M:%S"
    assert constants.LOG_LEVEL == "INFO"
    assert constants.LOG_FILE == "app.log"


def test_error_messages():
    """Test that error messages dictionary exists and contains expected keys"""
    assert isinstance(constants.ERROR_MESSAGES, dict)
    assert len(constants.ERROR_MESSAGES) > 0

    # Check for some common error messages
    assert "invalid_input" in constants.ERROR_MESSAGES
    assert "not_found" in constants.ERROR_MESSAGES
    assert "unauthorized" in constants.ERROR_MESSAGES
    assert "server_error" in constants.ERROR_MESSAGES

    # Check some message values
    assert constants.ERROR_MESSAGES["invalid_input"] == "Invalid input provided"
    assert constants.ERROR_MESSAGES["not_found"] == "Resource not found"
    assert constants.ERROR_MESSAGES["unauthorized"] == "Unauthorized access"
