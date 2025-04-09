"""Development configuration without Google Cloud dependencies."""
import base64
import os

from dotenv import load_dotenv

load_dotenv()

# Generate a default encryption key if not provided
DEFAULT_ENCRYPTION_KEY = base64.urlsafe_b64encode(b"find_a_meeting_spot_dev_key_32bytes!!").decode()


class DevelopmentConfig:
    """Development configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "a_default_secret_key_for_dev")
    DEBUG = True
    TESTING = False
    PORT = int(os.environ.get("PORT", 8001))

    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///dev.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Service Account Configuration (disabled in development)
    SERVICE_ACCOUNT_CREDENTIALS = None

    # Google OAuth Configuration
    GOOGLE_CLIENT_ID = os.environ.get(
        "GOOGLE_CLIENT_ID", "270814322595-hueraif6brli58po5gishfvcmocv6n04.apps.googleusercontent.com"
    )

    # Encryption Key (required for meeting requests)
    ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", DEFAULT_ENCRYPTION_KEY)
    print(f"Using encryption key: {ENCRYPTION_KEY}")  # Debug log

    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-key")

    # Frontend URL
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

    # Mailgun Configuration
    MAILGUN_DOMAIN = os.environ.get("MAILGUN_DOMAIN", "mg.findameetingspot.com")
    MAILGUN_API_KEY = os.environ.get("MAILGUN_API_KEY")
    FLASK_ENV = "development"  # Set this explicitly for email handling
