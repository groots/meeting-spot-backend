"""Tests for encryption utilities."""

import pytest
from flask import current_app

from utils.encryption import decrypt_data, encrypt_data


def test_encryption_key_required():
    """Test that encryption fails gracefully when key is missing."""
    with pytest.raises(ValueError, match="Encryption key is required"):
        encrypt_data("test data", key=None)


def test_encryption_key_from_config(app):
    """Test that encryption works with key from app config."""
    test_data = "sensitive data"

    # Ensure key exists in config
    assert "ENCRYPTION_KEY" in current_app.config
    assert current_app.config["ENCRYPTION_KEY"] is not None

    # Test encryption
    encrypted = encrypt_data(test_data)
    assert encrypted != test_data

    # Test decryption
    decrypted = decrypt_data(encrypted)
    assert decrypted == test_data


def test_invalid_encryption_key():
    """Test that encryption fails gracefully with invalid key."""
    with pytest.raises(ValueError, match="Invalid encryption key"):
        encrypt_data("test data", key="invalid_key")
