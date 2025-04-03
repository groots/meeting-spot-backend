import requests

from flask import current_app


def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Send an email using Mailgun.
    Falls back to logging in development environment.
    """
    try:
        # Get Mailgun configuration
        api_key = current_app.config.get("MAILGUN_API_KEY")
        domain = current_app.config.get("MAILGUN_DOMAIN")
        env = current_app.config.get("FLASK_ENV", "development")  # Default to development

        # In development, just log the email
        if env == "development":
            current_app.logger.info(f"Would send email to {to_email}")
            current_app.logger.info(f"Subject: {subject}")
            current_app.logger.info(f"Body: {body}")
            return True

        # In production, check for required config
        if not api_key or not domain:
            current_app.logger.error("Mailgun configuration missing")
            return False

        # Mailgun API endpoint
        url = f"https://api.mailgun.net/v3/{domain}/messages"

        # Prepare the email data
        data = {
            "from": f"Find A Meeting Spot <noreply@{domain}>",
            "to": to_email,
            "subject": subject,
            "text": body,
            "html": body.replace("\n", "<br>"),  # Basic HTML conversion
        }

        # Send the email
        response = requests.post(url, auth=("api", api_key), data=data)

        if response.status_code != 200:
            current_app.logger.error(f"Mailgun API error: {response.text}")
            return False

        return True
    except Exception as e:
        current_app.logger.error(f"Error sending email: {e}")
        return False


def send_sms(to_number: str, message: str) -> bool:
    """
    Send an SMS using the configured SMS service.
    For development, just log the SMS content.
    """
    try:
        env = current_app.config.get("FLASK_ENV", "development")  # Default to development

        # In development, just log the SMS
        if env == "development":
            current_app.logger.info(f"Would send SMS to {to_number}")
            current_app.logger.info(f"Message: {message}")
            return True

        # TODO: Implement actual SMS sending using Twilio or similar
        # For now, return True to indicate success
        return True
    except Exception as e:
        current_app.logger.error(f"Error sending SMS: {e}")
        return False
