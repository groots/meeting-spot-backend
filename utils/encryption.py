"""Module for handling data encryption and decryption.

This module provides functionality for encrypting and decrypting sensitive data
using the Fernet symmetric encryption algorithm from the cryptography library.
"""

import base64
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from flask import current_app


def get_encryption_key(secret_key) -> None:
    """Generate a Fernet key from a secret key using PBKDF2."""
    # Use PBKDF2 to derive a key from the secret
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"find_a_meeting_spot",  # Fixed salt for consistency
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
    return key


def encrypt_data(data: str, key: Optional[str] = None) -> str:
    """Encrypt the given data using the provided key.

    Args:
        data: The data to encrypt.
        key: The encryption key. If not provided, uses the key from app config.

    Returns:
        str: The encrypted data as a base64-encoded string.

    Raises:
        ValueError: If the encryption key is missing or invalid.
    """
    if not key:
        key = current_app.config.get("ENCRYPTION_KEY")
    if not key:
        raise ValueError("Encryption key is required")

    # Ensure the key is 32 bytes and base64-encoded
    key_bytes = key.encode()
    if len(key_bytes) != 32:
        key_bytes = base64.urlsafe_b64encode(key_bytes.ljust(32)[:32])

    f = Fernet(key_bytes)
    encrypted_data = f.encrypt(data.encode())
    return encrypted_data.decode()


def decrypt_data(encrypted_data: str, key: Optional[str] = None) -> str:
    """Decrypt the given data using the provided key.

    Args:
        encrypted_data: The encrypted data as a base64-encoded string.
        key: The encryption key. If not provided, uses the key from app config.

    Returns:
        str: The decrypted data.

    Raises:
        ValueError: If the encryption key is missing or invalid.
    """
    if not key:
        key = current_app.config.get("ENCRYPTION_KEY")
    if not key:
        raise ValueError("Encryption key is required")

    # Ensure the key is 32 bytes and base64-encoded
    key_bytes = key.encode()
    if len(key_bytes) != 32:
        key_bytes = base64.urlsafe_b64encode(key_bytes.ljust(32)[:32])

    f = Fernet(key_bytes)
    decrypted_data = f.decrypt(encrypted_data.encode())
    return decrypted_data.decode()
