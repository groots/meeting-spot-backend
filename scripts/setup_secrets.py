import os

from dotenv import load_dotenv
from google.cloud import secretmanager


def create_secret(secret_client, project_id, secret_id, secret_value) -> None:
    """Create a secret in Secret Manager if it doesn't exist."""
    parent = f"projects/{project_id}"

    try:
        # Check if secret exists
        secret_client.get_secret(request={"name": f"{parent}/secrets/{secret_id}"})
        print(f"Secret {secret_id} already exists")
    except Exception:
        # Create the secret
        secret = secret_client.create_secret(
            request={
                "parent": parent,
                "secret_id": secret_id,
                "secret": {"replication": {"automatic": {}}},
            }
        )
        print(f"Created secret: {secret.name}")

    # Add the secret version
    secret_client.add_secret_version(
        request={
            "parent": f"{parent}/secrets/{secret_id}",
            "payload": {"data": secret_value.encode("UTF-8")},
        }
    )
    print(f"Added version to secret: {secret_id}")


def main() -> None:
    # Load environment variables
    load_dotenv()

    # Initialize Secret Manager client
    secret_client = secretmanager.SecretManagerServiceClient()
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "find-a-meeting-spot")

    # Database secrets
    create_secret(secret_client, project_id, "db-user", os.getenv("DB_USER", "postgres"))
    create_secret(
        secret_client,
        project_id,
        "db-pass",
        os.getenv("DB_PASS", "ggSO12ro9u5N1VxANoQOlyGDuOzsHyv3Su7t9LO9IiQ"),
    )
    create_secret(secret_client, project_id, "db-name", os.getenv("DB_NAME", "findameetingspot"))
    create_secret(
        secret_client,
        project_id,
        "instance-connection-name",
        os.getenv(
            "INSTANCE_CONNECTION_NAME",
            "find-a-meeting-spot:us-central1:findameetingspot",
        ),
    )

    # API keys and security
    create_secret(
        secret_client,
        project_id,
        "google-maps-api-key",
        os.getenv("GOOGLE_MAPS_API_KEY", ""),
    )
    create_secret(secret_client, project_id, "encryption-key", os.getenv("ENCRYPTION_KEY", ""))
    create_secret(secret_client, project_id, "jwt-secret-key", os.getenv("JWT_SECRET_KEY", "dev"))

    print("All secrets have been set up successfully!")


if __name__ == "__main__":
    main()
