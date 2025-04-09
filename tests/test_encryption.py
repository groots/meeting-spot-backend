"""Test encryption utilities."""

from unittest.mock import MagicMock, patch

import pytest

from app.utils.encryption import get_encryption_key


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
    mock_app = MagicMock()
    mock_app.config.get.return_value = None
    with patch("app.utils.encryption.current_app", mock_app):
        with pytest.raises(ValueError, match="Encryption key is required"):
            get_encryption_key(None)

    # Test that same input produces same key
    key3 = get_encryption_key("test_secret")
    key4 = get_encryption_key("test_secret")
    assert key3 == key4
