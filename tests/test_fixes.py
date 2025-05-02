"""Tests for verifying the middleware and profile picture upload fixes."""

import io
import os
import tempfile
import unittest
from unittest.mock import patch

from flask import current_app
from sqlalchemy import inspect

from app import create_app, db
from app.models.user import User


class FixesTestCase(unittest.TestCase):
    """Test case for middleware registration and profile picture upload fixes."""

    def setUp(self):
        """Set up the test environment."""
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Create test user
        self.test_user = User(email="testuser@example.com", first_name="Test", last_name="User")
        self.test_user.set_password("password123")
        db.session.add(self.test_user)
        db.session.commit()

        # Get JWT token for authenticated requests
        response = self.client.post(
            "/api/v1/auth/login", json={"email": "testuser@example.com", "password": "password123"}
        )
        self.token = response.json.get("access_token")

    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_middleware_registration(self):
        """Test that middleware is properly registered with encryption key."""
        # Check that ENCRYPTION_KEY is set in app config
        self.assertIsNotNone(current_app.config.get("ENCRYPTION_KEY"))

        # Import the middleware module to test its availability
        from app.middleware import DEFAULT_ENCRYPTION_KEY, ensure_encryption_key, register_middleware

        # Ensure default key matches expected value
        self.assertEqual(DEFAULT_ENCRYPTION_KEY, "wx3XysUzuC2Um5gRWIiqqxsG1iy62F8T9f_WQoLlquA")

        # Simulate clearing the key and test that ensure_encryption_key resets it
        test_app = create_app("testing")
        test_app.config["ENCRYPTION_KEY"] = None

        with test_app.app_context():
            ensure_encryption_key(test_app)
            self.assertEqual(test_app.config.get("ENCRYPTION_KEY"), DEFAULT_ENCRYPTION_KEY)

    def test_user_model_has_profile_picture_url(self):
        """Test that User model has profile_picture_url column."""
        # Check if profile_picture_url exists in users table
        inspector = inspect(db.engine)
        columns = [column["name"] for column in inspector.get_columns("users")]
        self.assertIn("profile_picture_url", columns)

        # Check if field is present in the model class
        self.assertTrue(hasattr(User, "profile_picture_url"))

    def test_profile_picture_upload_endpoint_exists(self):
        """Test that the profile picture upload endpoint exists and returns correct response."""
        # Test OPTIONS request (CORS preflight)
        response = self.client.options("/api/v1/auth/me/picture")
        self.assertEqual(response.status_code, 200)
        self.assertIn("POST", response.headers.get("Access-Control-Allow-Methods"))

        # Test unauthorized access
        response = self.client.post("/api/v1/auth/me/picture")
        self.assertEqual(response.status_code, 401)  # Should require auth

    def test_profile_picture_upload_success(self):
        """Test successful profile picture upload."""
        # Create a test image
        test_image = (io.BytesIO(b"test image content"), "test_image.jpg")

        # Ensure instance/profile_pictures directory exists
        profile_pics_dir = os.path.join(current_app.instance_path, "profile_pictures")
        os.makedirs(profile_pics_dir, exist_ok=True)

        # Test successful upload
        with patch("werkzeug.datastructures.FileStorage.save") as mock_save:
            # Also patch the profile_picture_url update to avoid DB issues
            with patch("sqlalchemy.orm.attributes.set_attribute"):
                response = self.client.post(
                    "/api/v1/auth/me/picture",
                    headers={"Authorization": f"Bearer {self.token}"},
                    data={"profile_picture": test_image},
                    content_type="multipart/form-data",
                )

                # Verify the endpoint responded correctly
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json.get("success"))
                self.assertIn("url", response.json)

                # Verify that save was called
                mock_save.assert_called_once()

        # Since we're using a mock, we can't check the actual profile_picture_url
        # Instead, verify the response URL format
        url = response.json.get("url")
        self.assertTrue(url.startswith("/profile_pictures/"))
        self.assertTrue(url.endswith(".jpg"))

    def test_profile_picture_validation(self):
        """Test file validation in profile picture upload."""
        # Test invalid file type
        invalid_file = (io.BytesIO(b"test txt content"), "test.txt")
        response = self.client.post(
            "/api/v1/auth/me/picture",
            headers={"Authorization": f"Bearer {self.token}"},
            data={"profile_picture": invalid_file},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid file extension", response.json.get("error", ""))

        # Test missing file
        response = self.client.post(
            "/api/v1/auth/me/picture",
            headers={"Authorization": f"Bearer {self.token}"},
            data={},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("No profile picture", response.json.get("error", ""))


if __name__ == "__main__":
    unittest.main()
