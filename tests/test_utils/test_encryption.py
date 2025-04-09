"""Tests for encryption utilities."""

import pytest
from flask import current_app

from app.utils.encryption import decrypt_data, encrypt_data, get_encryption_key


def test_encryption_key_required():
    """Test that encryption fails gracefully when key is missing."""
    with pytest.raises(ValueError, match="ENCRYPTION_KEY not found in config"):
        get_encryption_key(None)


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
    with pytest.raises(ValueError, match="Failed to encrypt data"):
        encrypt_data("test data", secret_key="invalid_key")
