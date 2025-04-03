import os

from dotenv import load_dotenv
from google.cloud import secretmanager

load_dotenv()  # Load environment variables from .env file


def get_secret(secret_id) -> None:
    """Retrieve a secret from Secret Manager."""
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = (
            f"projects/{os.environ.get('GOOGLE_CLOUD_PROJECT')}/secrets/"
            f"{secret_id}/versions/latest"
        )
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"Error accessing secret {secret_id}: {e}")
        return None


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "a_default_secret_key_for_dev")
    DEBUG = os.environ.get("FLASK_DEBUG", "False") == "True"
    PORT = int(os.environ.get("PORT", 8080))

    # Database Configuration (using Cloud SQL Connector often avoids direct
    # host/port)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg2://user:password@host:port/dbname"
    )  # Example, replace with actual connection string or Cloud SQL Connector setup
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Google Cloud Project ID
    GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT")

    # Service Account Configuration
    SERVICE_ACCOUNT_EMAIL = os.environ.get(
        "SERVICE_ACCOUNT_EMAIL",
        "meeting-spot-app@find-a-meeting-spot.iam.gserviceaccount.com",
    )
    SERVICE_ACCOUNT_CREDENTIALS = get_secret("meeting-spot-service-account")

    # Google Maps API Key (Store securely in Secret Manager)
    GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")

    # Notification Service API Keys (Store securely)
    SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

    # Cloud Tasks Configuration
    CLOUD_TASKS_LOCATION = os.environ.get("CLOUD_TASKS_LOCATION")  # e.g., 'us-central1'
    CLOUD_TASKS_QUEUE = os.environ.get("CLOUD_TASKS_QUEUE", "meeting-spot-queue")
    # Service account email for Cloud Tasks HTTP targets (if applicable)
    CLOUD_TASKS_OIDC_SERVICE_ACCOUNT_EMAIL = os.environ.get(
        "CLOUD_TASKS_OIDC_SERVICE_ACCOUNT_EMAIL"
    )

    # Encryption Key (Store securely, maybe KMS)
    ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")

    # JWT Configuration (for authentication)
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "another_dev_secret_jwt_key")
    # Add other JWT settings like algorithm, expiry time etc. as needed

    # Frontend URL (for generating links)
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

    # Add other configurations as needed
