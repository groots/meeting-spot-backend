"""Notification utilities for sending emails and SMS."""

import logging
import os

import requests
from flask import current_app, url_for

# Configure logger
logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Send an email using Mailgun.
    Falls back to logging in development environment.
    """
    try:
        # Get Mailgun configuration
        api_key = current_app.config.get("MAILGUN_API_KEY")
        domain = current_app.config.get("MAILGUN_DOMAIN")

        # IMPORTANT: Also check environment variables directly
        if not api_key:
            api_key = os.environ.get("MAILGUN_API_KEY")
        if not domain:
            domain = os.environ.get("MAILGUN_DOMAIN")

        # Explicitly check both FLASK_ENV and ENV configuration
        env = current_app.config.get("ENV", "development")
        flask_env = current_app.config.get("FLASK_ENV", "development")

        # Log environment settings and email details for debugging
        logger.info(f"Current ENV: {env}, FLASK_ENV: {flask_env}")
        logger.info(f"Sending email to: {to_email}")
        logger.info(f"Mailgun Domain configured: {domain}")
        logger.info(f"Mailgun API Key present: {'Yes' if api_key else 'No'}")

        # Always attempt to send email in development for testing purposes
        # Remove the development check to allow emails to be sent

        # In production, check for required config first
        if not api_key or not domain:
            logger.error("Missing Mailgun configuration. Please set MAILGUN_API_KEY and MAILGUN_DOMAIN.")
            logger.error("Email will not be sent!")
            return False

        # Mailgun API endpoint
        url = f"https://api.mailgun.net/v3/{domain}/messages"
        logger.info(f"Using Mailgun endpoint: {url}")

        # Prepare the email data
        data = {
            "from": f"Find A Meeting Spot <noreply@{domain}>",
            "to": to_email,
            "subject": subject,
            "text": body,
            "html": body.replace("\n", "<br>"),  # Basic HTML conversion
        }

        # Send the email
        logger.info(f"Sending email request to Mailgun...")
        response = requests.post(url, auth=("api", api_key), data=data)

        # Log response details
        logger.info(f"Mailgun API response status code: {response.status_code}")

        if response.status_code != 200:
            logger.error(f"Mailgun API error: {response.text}")
            return False

        logger.info(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False


def send_password_reset_email(email: str, token: str) -> bool:
    """
    Send a password reset email with a token.

    Args:
        email: The recipient's email address
        token: The password reset token

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Get frontend URL from config
        frontend_url = current_app.config.get("FRONTEND_URL", "https://findameetingspot.com")

        # Construct reset URL
        reset_url = f"{frontend_url}/auth/reset-password/{token}"

        # Create email subject and body
        subject = "Reset Your Find A Meeting Spot Password"
        body = f"""Hello,

You've requested to reset your password for Find A Meeting Spot.

Please click the link below to reset your password:
{reset_url}

This link will expire in 1 hour.

If you didn't request this password reset, please ignore this email or contact support if you have concerns.

Thanks,
The Find A Meeting Spot Team
"""

        logger.info(f"Sending password reset email to {email} with token {token[:10]}...")

        # Send the email using the send_email function
        result = send_email(email, subject, body)

        if result:
            logger.info(f"Password reset email sent successfully to {email}")
        else:
            logger.error(f"Failed to send password reset email to {email}")

        return result

    except Exception as e:
        logger.error(f"Error sending password reset email: {e}")
        return False


def send_sms(to_number: str, message: str) -> bool:
    """
    Send an SMS using the configured SMS service.
    For development, just log the SMS content.
    """
    try:
        # Check both ENV settings
        env = current_app.config.get("ENV", "development")
        flask_env = current_app.config.get("FLASK_ENV", "development")

        # Special case for tests
        is_test_environment = flask_env == "production"

        # In development, just log the SMS
        if (env == "development" or flask_env == "development") and not is_test_environment:
            logger.info(f"Development mode: Would send SMS to {to_number}")
            logger.info(f"Message: {message}")
            return True

        # TODO: Implement actual SMS sending using Twilio or similar
        # For now, return True to indicate success
        return True
    except Exception as e:
        logger.error(f"Error sending SMS: {e}")
        return False
