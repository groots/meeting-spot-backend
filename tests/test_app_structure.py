"""Test the application structure."""

import os

import pytest
from flask import Flask

from app import create_app
from app.models import MeetingRequest, MeetingRequestStatus
from app.routes import api_bp
from app.utils import decrypt_data, encrypt_data, get_encryption_key


def test_app_structure():
    """Test that all required files and directories exist."""
    required_files = [
        "app/__init__.py",
        "app/routes/__init__.py",
        "app/routes/main.py",
        "app/api/__init__.py",
        "app/models/__init__.py",
        "app/models/meeting_request.py",
        "app/models/user.py",
        "app/models/types.py",
        "app/models/enums.py",
    ]

    for file_path in required_files:
        assert os.path.exists(file_path), f"Required file {file_path} does not exist"


def test_app_creation():
    """Test that the Flask app can be created without errors."""
    app = create_app()
    assert isinstance(app, Flask)

    # Test that blueprints are registered
    assert app.blueprints.get("api_v2") is not None
    assert app.blueprints.get("api_v1") is not None
    assert app.blueprints.get("api") is not None


def test_imports():
    """Test that all required modules can be imported."""
    # Import statements are used for testing importability
    from app import create_app  # noqa: F401
    from app.models import MeetingRequest, MeetingRequestStatus  # noqa: F401
    from app.routes import api_bp  # noqa: F401
    from app.utils import decrypt_data, encrypt_data, get_encryption_key  # noqa: F401


def test_static_files():
    """Test that static files are accessible."""
    app = create_app()
    with app.test_client() as client:
        # Test API endpoint
        response = client.get("/api/health")
        assert response.status_code == 200
