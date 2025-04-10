import os

from dotenv import load_dotenv
from sqlalchemy.pool import StaticPool

# Load environment variables
load_dotenv()


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

    # Frontend URL
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # Mailgun Configuration
    MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
    MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")

    # CORS Configuration
    CORS_ORIGINS = [
        "http://localhost:3000",  # Local development
        "http://localhost:5000",  # Local Flask server
        "https://find-a-meeting-spot.web.app",  # Production frontend
        "https://find-a-meeting-spot.ue.r.appspot.com",  # App Engine URL
        "https://findameetingspot.com",  # Custom domain
        "https://www.findameetingspot.com",  # www subdomain
    ]


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    DEBUG = True
    # Use SQLite for testing
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # Configure SQLite for testing
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
    }


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:ggSO12ro9u5N1VxANoQOlyGDuOzsHyv3Su7t9LO9IiQ@"
        "localhost:5433/findameetingspot_dev",
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
    ]

    # Database configuration - Use socket for Cloud SQL
    # This is a fallback if DATABASE_URL env var is not set
    SQLALCHEMY_DATABASE_URI = "postgresql+pg8000://meetingspot:MeetingSpot123!@/findameetingspot?unix_sock=/cloudsql/find-a-meeting-spot:us-east1:findameetingspot/.s.PGSQL.5432"

    # Set up SQLAlchemy with connection pool
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    }


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
