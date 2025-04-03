"""Test notification utilities."""

import pytest
from unittest.mock import patch, MagicMock, call
from app.utils.notifications import send_email, send_sms


def test_send_email_development():
    """Test email sending in development environment."""
    mock_app = MagicMock()
    mock_app.config.get.side_effect = lambda x, default=None: "development" if x == "FLASK_ENV" else None
    mock_app.logger = MagicMock()

    with patch("app.utils.notifications.current_app", mock_app):
        # Test successful email sending in development
        result = send_email("test@example.com", "Test Subject", "Test Body")
        assert result is True
        assert mock_app.logger.info.call_count == 3
        mock_app.logger.info.assert_has_calls([
            call("Would send email to test@example.com"),
            call("Subject: Test Subject"),
            call("Body: Test Body")
        ], any_order=True)


def test_send_email_production():
    """Test email sending in production environment."""
    mock_app = MagicMock()
    mock_app.config.get.side_effect = lambda x, default=None: {
        "FLASK_ENV": "production",
        "MAILGUN_API_KEY": "test_key",
        "MAILGUN_DOMAIN": "test.domain"
    }.get(x)
    mock_app.logger = MagicMock()

    mock_post = MagicMock()
    mock_post.return_value = MagicMock()
    mock_post.return_value.status_code = 200

    with patch("app.utils.notifications.current_app", mock_app), patch("requests.post", mock_post):
        # Test successful email sending
        result = send_email("test@example.com", "Test Subject", "Test Body")
        assert result is True
        mock_post.assert_called_once()

        # Test failed email sending
        mock_post.reset_mock()
        mock_post.return_value.status_code = 400
        mock_post.return_value.text = "Error"
        result = send_email("test@example.com", "Test Subject", "Test Body")
        assert result is False
        mock_app.logger.error.assert_called_once_with("Mailgun API error: Error")


def test_send_email_missing_config():
    """Test email sending with missing configuration."""
    mock_app = MagicMock()
    mock_app.config.get.side_effect = lambda x, default=None: "production" if x == "FLASK_ENV" else None
    mock_app.logger = MagicMock()

    with patch("app.utils.notifications.current_app", mock_app):
        result = send_email("test@example.com", "Test Subject", "Test Body")
        assert result is False
        mock_app.logger.error.assert_called_once_with("Mailgun configuration missing")


def test_send_sms():
    """Test SMS sending."""
    mock_app = MagicMock()
    mock_app.config.get.side_effect = lambda x, default=None: "development" if x == "FLASK_ENV" else None
    mock_app.logger = MagicMock()

    with patch("app.utils.notifications.current_app", mock_app):
        # Test successful SMS sending
        result = send_sms("+1234567890", "Test Message")
        assert result is True
        assert mock_app.logger.info.call_count == 2
        mock_app.logger.info.assert_has_calls([
            call("Would send SMS to +1234567890"),
            call("Message: Test Message")
        ], any_order=True)

        # Test error handling
        mock_app.logger.reset_mock()
        with patch("app.utils.notifications.current_app.logger.info", side_effect=Exception("Test error")):
            result = send_sms("+1234567890", "Test Message")
            assert result is False
            mock_app.logger.error.assert_called_once_with("Error sending SMS: Test error") 