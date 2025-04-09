"""Encryption utilities for the application."""

import base64
from typing import Union

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from flask import current_app


def get_encryption_key(key: Union[str, bytes, None] = None) -> bytes:
    """Generate a Fernet key from a secret key using PBKDF2."""
    # Get the key from config if not provided
    if key is None:
        key = current_app.config.get("ENCRYPTION_KEY")

    if not key:
        raise ValueError("Encryption key is required")

    # Convert string key to bytes if needed
    if isinstance(key, str):
        key_bytes = key.encode()
    else:
        key_bytes = key

    try:
        # Use PBKDF2 to derive a key from the secret
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"find_a_meeting_spot",  # Fixed salt for consistency
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(key_bytes))

        # Verify the key is valid for Fernet
        Fernet(key)
        return key
    except Exception as e:
        raise ValueError(f"Failed to generate encryption key: {e}")


def encrypt_data(data: Union[str, bytes], key: Union[str, bytes, None] = None) -> str:
    """Encrypt data using Fernet symmetric encryption."""
    if not data:
        return data

    try:
        # Convert data to bytes if it's a string
        if isinstance(data, str):
            data_bytes = data.encode()
        else:
            data_bytes = data

        # Get the encryption key
        encryption_key = get_encryption_key(key)
        f = Fernet(encryption_key)
        return f.encrypt(data_bytes).decode()
    except ValueError as e:
        raise e
    except Exception as e:
        raise ValueError(f"Failed to encrypt data: {e}")


def decrypt_data(data: Union[str, bytes], key: Union[str, bytes, None] = None) -> str:
    """Decrypt data using Fernet symmetric encryption."""
    if not data:
        return data

    try:
        # Convert data to bytes if it's a string
        if isinstance(data, str):
            data_bytes = data.encode()
        else:
            data_bytes = data

        # Get the encryption key
        encryption_key = get_encryption_key(key)
        f = Fernet(encryption_key)
        return f.decrypt(data_bytes).decode()
    except ValueError as e:
        raise e
    except Exception as e:
        raise ValueError(f"Failed to decrypt data: {e}")
