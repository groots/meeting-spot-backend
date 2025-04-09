"""Tests for encryption utilities."""

import pytest
from flask import current_app

from app.utils.encryption import decrypt_data, encrypt_data, get_encryption_key


def test_encryption_key_required(app):
    """Test that encryption fails gracefully when key is missing."""
    # Ensure no encryption key in config
    app.config["ENCRYPTION_KEY"] = None

    with pytest.raises(ValueError, match="Encryption key is required"):
        get_encryption_key(None)


def test_encryption_key_from_config(app):
    """Test that encryption works with key from app config."""
    test_data = "sensitive data"

    # Set encryption key in app config
    app.config["ENCRYPTION_KEY"] = "test-encryption-key"

    # Ensure key exists in config
    assert "ENCRYPTION_KEY" in current_app.config
    assert current_app.config["ENCRYPTION_KEY"] is not None
    assert isinstance(current_app.config["ENCRYPTION_KEY"], str)

    # Test encryption
    encrypted = encrypt_data(test_data)
    assert encrypted != test_data
    assert isinstance(encrypted, str)

    # Test decryption
    decrypted = decrypt_data(encrypted)
    assert decrypted == test_data


def test_invalid_encryption_key():
    """Test that encryption fails gracefully with invalid key."""
    with pytest.raises(ValueError) as exc_info:
        # Use an empty string as key, which will fail PBKDF2
        encrypt_data("test data", key="")
