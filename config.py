import os

from dotenv import load_dotenv
from google.cloud import secretmanager
from sqlalchemy.pool import StaticPool

load_dotenv()  # Load environment variables from .env file


def get_secret(secret_id, ignore_in_dev=False) -> None:
    """Retrieve a secret from Secret Manager."""
    if os.environ.get("FLASK_ENV") == "development" and ignore_in_dev:
        return None

    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{os.environ.get('GOOGLE_CLOUD_PROJECT')}/secrets/{secret_id}/versions/l" + "atest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"Error accessing secret {secret_id}: {e}")
        return None


class Config:
    """Base configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Google Cloud Project
    GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "find-a-meeting-spot")

    # Google Maps API Key
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

    # Encryption Key
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

    # JWT Configuration
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev")
    JWT_TOKEN_LOCATION = ["headers", "cookies"]
    JWT_ACCESS_COOKIE_PATH = "/api/"
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_COOKIE_SECURE = True

    # Frontend URL
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # CORS Configuration
    CORS_ORIGINS = [
        "http://localhost:3000",  # Local development
        "http://localhost:5000",  # Local Flask server
        "https://find-a-meeting-spot.web.app",  # Production frontend
        "https://find-a-meeting-spot.ue.r.appspot.com",  # App Engine URL
        "https://findameetingspot.com",  # Custom domain
        "https://www.findameetingspot.com",  # www subdomain
        "https://accounts.google.com",  # Google OAuth
        "https://meeting-spot-backend-270814322595.us-east1.run.app",  # Backend URL
    ]

    # Security Headers
    SECURITY_HEADERS = {
        "Content-Security-Policy": "default-src 'self' https://accounts.google.com; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://accounts.google.com; style-src 'self' 'unsafe-inline';",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "SAMEORIGIN",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    }

    # Database Configuration (using Cloud SQL Connector often avoids direct
    # host/port)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg2://user:password@host:port/dbname"
    )  # Example, replace with actual connection string or Cloud SQL Connector setup

    # Service Account Configuration
    SERVICE_ACCOUNT_EMAIL = os.environ.get(
        "SERVICE_ACCOUNT_EMAIL",
        "meeting-spot-app@find-a-meeting-spot.iam.gserviceaccount.com",
    )
    SERVICE_ACCOUNT_CREDENTIALS = get_secret("meeting-spot-service-account", ignore_in_dev=True)

    # Notification Service API Keys (Store securely)
    SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

    # Cloud Tasks Configuration
    CLOUD_TASKS_LOCATION = os.environ.get("CLOUD_TASKS_LOCATION")  # e.g., 'us-central1'
    CLOUD_TASKS_QUEUE = os.environ.get("CLOUD_TASKS_QUEUE", "meeting-spot-queue")
    # Service account email for Cloud Tasks HTTP targets (if applicable)
    CLOUD_TASKS_OIDC_SERVICE_ACCOUNT_EMAIL = os.environ.get("CLOUD_TASKS_OIDC_SERVICE_ACCOUNT_EMAIL")

    # Add other configurations as needed


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    TESTING = False

    # Override service account to avoid Secret Manager in development
    SERVICE_ACCOUNT_CREDENTIALS = None

    # Use environment variables for development
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///dev.db")

    # Use environment variables for encryption key
    ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "lpCxwLkoWlix-nm4VtLRkbtuy_Yx9pb5mhZjYvJuRGA=")

    # Frontend URL for development
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

    # JWT settings
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-key")

    # Google OAuth settings
    GOOGLE_CLIENT_ID = os.environ.get(
        "GOOGLE_CLIENT_ID", "270814322595-hueraif6brli58po5gishfvcmocv6n04.apps.googleusercontent.com"
    )


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    TESTING = False
    ENV = "production"

    # Security settings
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"

    # CORS settings
    CORS_ORIGINS = [
        "https://find-a-meeting-spot.ue.r.appspot.com",
        "https://find-a-meeting-spot.web.app",
        "https://findameetingspot.com",
        "https://www.findameetingspot.com",
        "https://meeting-spot-backend-270814322595.us-east1.run.app",
        "https://accounts.google.com",
    ]

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/findameetingspot"
    )

    # Set up SQLAlchemy with connection pool
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    }


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    DEBUG = True

    # Server configuration for URL building
    SERVER_NAME = "localhost:5000"
    APPLICATION_ROOT = "/"
    PREFERRED_URL_SCHEME = "http"

    # Use SQLite for testing
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

    # Configure SQLite for testing
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
    }

    # Ensure encryption key is set for testing
    ENCRYPTION_KEY = "test_encryption_key_for_testing_only"


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
