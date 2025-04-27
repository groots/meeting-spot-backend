"""Development configuration for Flask."""
import base64
import os

from dotenv import load_dotenv

from app.config import DevelopmentConfig as BaseDevConfig

load_dotenv()

# Generate a default encryption key if not provided
DEFAULT_ENCRYPTION_KEY = base64.urlsafe_b64encode(b"find_a_meeting_spot_dev_key_32bytes!!").decode()


class DevelopmentConfig(BaseDevConfig):
    """Development configuration for Flask."""

    # Skip Facebook migration in development to avoid errors
    SKIP_FACEBOOK_MIGRATION = True

    # Disable premium feature requirements for development
    PREMIUM_FEATURES_DISABLED = True

    # Additional development configuration
    DEBUG = True
    TESTING = False

    # Allow all CORS origins for development
    CORS_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5000",
        "http://localhost:5001",
        "http://localhost:8080",
        "http://localhost:8081",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8081",
    ]

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///development.db")

    # Explicitly enable CORS handling
    CORS_ENABLED = True

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
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60 * 6  # 6 hours standard session time
    JWT_REFRESH_TOKEN_EXPIRES = 60 * 60 * 24 * 14  # 14 days for "remember me" functionality

    # Frontend URL
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

    # Mailgun Configuration
    MAILGUN_DOMAIN = os.environ.get("MAILGUN_DOMAIN", "mg.findameetingspot.com")
    MAILGUN_API_KEY = os.environ.get("MAILGUN_API_KEY")
    FLASK_ENV = "development"  # Set this explicitly for email handling
