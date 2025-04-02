import base64
from typing import Any, Dict, List, Optional, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


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


def encrypt_data(data: str, secret_key: str) -> str:
    """Encrypt data using Fernet symmetric encryption."""
    if not data:
        return data

    try:
        f = Fernet(get_encryption_key(secret_key))
        return f.encrypt(data.encode()).decode()
    except Exception as e:
        raise ValueError(f"Encryption failed: {str(e)}")


def decrypt_data(encrypted_data: str, secret_key: str) -> str:
    """Decrypt data using Fernet symmetric encryption."""
    if not encrypted_data:
        return encrypted_data

    try:
        f = Fernet(get_encryption_key(secret_key))
        return f.decrypt(encrypted_data.encode()).decode()
    except Exception as e:
        raise ValueError(f"Decryption failed: {str(e)}")
