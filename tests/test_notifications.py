"""Test notification utilities.

Note: Black formatting is temporarily disabled for this file due to a known issue
with black's internal formatter. A bug report will be filed at:
https://github.com/psf/black/issues
"""

from unittest.mock import MagicMock, call, patch

from app.utils.notifications import send_email, send_sms


def test_send_email_development():
    """Test email sending in development mode."""
    mock_app = MagicMock()
    mock_app.config.get.return_value = "development"
    mock_logger = MagicMock()

    with patch("app.utils.notifications.current_app", mock_app), patch("app.utils.notifications.logger", mock_logger):
        result = send_email("test@example.com", "Test Subject", "Test Body")
        assert result is True
        mock_logger.info.assert_has_calls(
            [
                call("Development mode: Would send email to test@example.com"),
                call("Subject: Test Subject"),
                call("Body: Test Body"),
            ]
        )


def test_send_email_production():
    """Test email sending in production mode."""
    mock_app = MagicMock()
    mock_app.config.get.side_effect = lambda key, default=None: {
        "FLASK_ENV": "production",
        "MAILGUN_API_KEY": "test_key",
        "MAILGUN_DOMAIN": "test.domain",
    }.get(key, default)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post = MagicMock(return_value=mock_response)

    with patch("app.utils.notifications.current_app", mock_app), patch("requests.post", mock_post):
        result = send_email("test@example.com", "Test Subject", "Test Body")
        assert result is True
        mock_post.assert_called_once()


def test_send_email_missing_config():
    """Test email sending with missing configuration."""
    mock_app = MagicMock()
    mock_app.config.get.side_effect = lambda key, default=None: {
        "FLASK_ENV": "production",
        "MAILGUN_API_KEY": None,
        "MAILGUN_DOMAIN": None,
    }.get(key, default)
    mock_logger = MagicMock()

    with patch("app.utils.notifications.current_app", mock_app), patch("app.utils.notifications.logger", mock_logger):
        result = send_email("test@example.com", "Test Subject", "Test Body")
        assert result is False
        mock_logger.error.assert_called_once_with(
            "Missing Mailgun configuration. " "Please set MAILGUN_API_KEY and MAILGUN_DOMAIN."
        )


def test_send_sms():
    """Test SMS sending."""
    mock_app = MagicMock()
    mock_app.config.get.return_value = "development"
    mock_logger = MagicMock()

    with patch("app.utils.notifications.current_app", mock_app), patch("app.utils.notifications.logger", mock_logger):
        result = send_sms("+1234567890", "Test Message")
        assert result is True
        mock_logger.info.assert_has_calls(
            [
                call("Development mode: Would send SMS to +1234567890"),
                call("Message: Test Message"),
            ]
        )
