"""Module for handling email and SMS notifications.

This module provides functionality for sending email and SMS notifications
using different providers based on the application configuration.
"""

import logging
from typing import Optional

import requests
from flask import current_app

# Configure logger
logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email to the specified recipient.

    Args:
        to: The email address of the recipient.
        subject: The subject line of the email.
        body: The body content of the email.

    Returns:
        bool: True if the email was sent successfully, False otherwise.
    """
    # In development, just log the email
    if current_app.config.get("ENV") == "development":
        logger.info(f"Development mode: Would send email to {to}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Body: {body}")
        return True

    # In production, check for required config
    api_key = current_app.config.get("MAILGUN_API_KEY")
    domain = current_app.config.get("MAILGUN_DOMAIN")

    if not api_key or not domain:
        logger.error("Missing Mailgun configuration. " "Please set MAILGUN_API_KEY and MAILGUN_DOMAIN.")
        return False

    # Mailgun API endpoint
    url = f"https://api.mailgun.net/v3/{domain}/messages"

    # Send the email
    try:
        response = requests.post(
            url,
            auth=("api", api_key),
            data={
                "from": f"Find a Meeting Spot <noreply@{domain}>",
                "to": to,
                "subject": subject,
                "text": body,
            },
        )
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def send_sms(to: str, message: str) -> bool:
    """Send an SMS to the specified phone number.

    Args:
        to: The phone number of the recipient.
        message: The content of the SMS.

    Returns:
        bool: True if the SMS was sent successfully, False otherwise.
    """
    # In development, just log the SMS
    if current_app.config.get("ENV") == "development":
        logger.info(f"Development mode: Would send SMS to {to}")
        logger.info(f"Message: {message}")
        return True

    # In production, implement actual SMS sending
    # This is a placeholder for actual SMS implementation
    logger.warning("SMS sending not implemented in production")
    return False
