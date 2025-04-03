"""Test encryption utilities."""

import pytest
from app.utils.encryption import decrypt_data, encrypt_data, get_encryption_key


def test_get_encryption_key():
    """Test encryption key generation."""
    # Test with string key
    key1 = get_encryption_key("test_secret")
    assert isinstance(key1, bytes)
    assert len(key1) > 0

    # Test with bytes key
    key2 = get_encryption_key(b"test_secret")
    assert isinstance(key2, bytes)
    assert len(key2) > 0

    # Test with None key (should use config)
    with pytest.raises(ValueError):
        get_encryption_key(None)


def test_encrypt_decrypt_data():
    """Test data encryption and decryption."""
    test_data = "Hello, World!"
    secret_key = "test_secret_key"

    # Test encryption
    encrypted = encrypt_data(test_data, secret_key)
    assert isinstance(encrypted, str)
    assert encrypted != test_data
    assert len(encrypted) > 0

    # Test decryption
    decrypted = decrypt_data(encrypted, secret_key)
    assert decrypted == test_data

    # Test with bytes input
    encrypted_bytes = encrypt_data(test_data.encode(), secret_key)
    decrypted_bytes = decrypt_data(encrypted_bytes, secret_key)
    assert decrypted_bytes == test_data

    # Test empty data
    assert encrypt_data("", secret_key) == ""
    assert decrypt_data("", secret_key) == ""

    # Test invalid data
    with pytest.raises(ValueError):
        decrypt_data("invalid_data", secret_key) 