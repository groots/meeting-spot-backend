"""Script for setting up secrets in Google Cloud Secret Manager.

This script helps manage secrets for the Find a Meeting Spot application by
providing functionality to create, update, and delete secrets in Google Cloud
Secret Manager.
"""

import argparse
import os
from typing import Optional

from google.cloud import secretmanager


def create_secret(project_id: str, secret_id: str, secret_value: str) -> None:
    """Create a new secret in Google Cloud Secret Manager.

    Args:
        project_id: The Google Cloud project ID.
        secret_id: The ID of the secret to create.
        secret_value: The value to store in the secret.
    """
    client = secretmanager.SecretManagerServiceClient()
    parent = f"projects/{project_id}"

    # Create the secret
    secret = client.create_secret(
        request={
            "parent": parent,
            "secret_id": secret_id,
            "secret": {"replication": {"automatic": {}}},
        }
    )

    # Add the secret version
    client.add_secret_version(
        request={
            "parent": secret.name,
            "payload": {"data": secret_value.encode("UTF-8")},
        }
    )

    print(f"Created secret {secret_id}")


def update_secret(project_id: str, secret_id: str, secret_value: str) -> None:
    """Update an existing secret in Google Cloud Secret Manager.

    Args:
        project_id: The Google Cloud project ID.
        secret_id: The ID of the secret to update.
        secret_value: The new value to store in the secret.
    """
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}"

    # Add a new version to the secret
    client.add_secret_version(
        request={
            "parent": name,
            "payload": {"data": secret_value.encode("UTF-8")},
        }
    )

    print(f"Updated secret {secret_id}")


def delete_secret(project_id: str, secret_id: str) -> None:
    """Delete a secret from Google Cloud Secret Manager.

    Args:
        project_id: The Google Cloud project ID.
        secret_id: The ID of the secret to delete.
    """
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}"

    client.delete_secret(request={"name": name})
    print(f"Deleted secret {secret_id}")


def main() -> None:
    """Main function for the setup_secrets script."""
    parser = argparse.ArgumentParser(description="Manage secrets in Google Cloud Secret Manager")
    parser.add_argument(
        "--project-id",
        required=True,
        help="Google Cloud project ID",
    )
    parser.add_argument(
        "--secret-id",
        required=True,
        help="ID of the secret to manage",
    )
    parser.add_argument(
        "--secret-value",
        help="Value to store in the secret",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete the secret instead of creating/updating it",
    )

    args = parser.parse_args()

    if args.delete:
        delete_secret(args.project_id, args.secret_id)
    elif args.secret_value:
        try:
            create_secret(args.project_id, args.secret_id, args.secret_value)
        except Exception as e:
            if "already exists" in str(e):
                update_secret(args.project_id, args.secret_id, args.secret_value)
            else:
                raise
    else:
        parser.error("Either --secret-value or --delete must be specified")


if __name__ == "__main__":
    main()
