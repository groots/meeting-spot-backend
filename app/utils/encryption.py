"""Encryption utilities for the application."""

import base64
from typing import Union

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from flask import current_app


def get_encryption_key(secret_key: Union[str, bytes, None] = None) -> bytes:
    """Generate a Fernet key from a secret key using PBKDF2."""
    # Get the key from config if not provided
    if secret_key is None:
        secret_key = current_app.config.get("ENCRYPTION_KEY")
        if not secret_key:
            raise ValueError("ENCRYPTION_KEY not found in config")

    # Convert string key to bytes if needed
    if isinstance(secret_key, str):
        key_bytes = secret_key.encode()
    else:
        key_bytes = secret_key

    # Use PBKDF2 to derive a key from the secret
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"find_a_meeting_spot",  # Fixed salt for consistency
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(key_bytes))


def encrypt_data(data: Union[str, bytes], secret_key: Union[str, bytes, None] = None) -> str:
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
        key = get_encryption_key(secret_key)
        f = Fernet(key)
        return f.encrypt(data_bytes).decode()
    except Exception as e:
        raise ValueError(f"Failed to encrypt data: {e}")


def decrypt_data(data: Union[str, bytes], secret_key: Union[str, bytes, None] = None) -> str:
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
        key = get_encryption_key(secret_key)
        f = Fernet(key)
        return f.decrypt(data_bytes).decode()
    except Exception as e:
        raise ValueError(f"Failed to decrypt data: {e}")
