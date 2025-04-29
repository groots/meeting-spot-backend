"""
Unit tests for the database verification functionality.
"""

import unittest
from unittest.mock import MagicMock, call, patch

import sqlalchemy as sa

# Import the functions we want to test
from verify_db_schema import check_user_data, get_db_url, verify_columns


class TestDatabaseVerification(unittest.TestCase):
    """Test cases for the database verification functionality."""

    @patch("os.environ.get")
    def test_get_db_url_local(self, mock_environ_get):
        """Test getting the database URL for local development."""
        # Mock environment variables
        mock_environ_get.return_value = None

        # Call the function
        result = get_db_url()

        # Check the result
        self.assertEqual(result, "postgresql://postgres:postgres@localhost:5432/find_a_meeting_spot")

    @patch("os.environ.get")
    def test_get_db_url_cloud_sql(self, mock_environ_get):
        """Test getting the database URL for Cloud SQL with proxy."""

        # Mock environment variables
        def mock_get(key, default=None):
            values = {
                "INSTANCE_CONNECTION_NAME": "test-project:region:instance",
                "DB_USER": "test-user",
                "DB_PASS": "test-password",
                "DB_NAME": "test-db",
                "DB_HOST": "127.0.0.1",
                "DB_PORT": "5432",
            }
            return values.get(key, default)

        mock_environ_get.side_effect = mock_get

        # Call the function
        result = get_db_url()

        # Check the result
        expected = "postgresql://test-user:test-password@127.0.0.1:5432/test-db"
        self.assertEqual(result, expected)

    @patch("sqlalchemy.inspect")
    def test_verify_columns_all_exist(self, mock_inspect):
        """Test verifying columns when all required columns exist."""
        # Mock inspect return value
        mock_inspector = MagicMock()
        mock_inspect.return_value = mock_inspector

        # Mock get_columns to return all required columns
        mock_inspector.get_columns.return_value = [
            {"name": "id"},
            {"name": "email"},
            {"name": "username"},
            {"name": "first_name"},
            {"name": "last_name"},
            {"name": "facebook_oauth_id"},
        ]

        # Call function with mock engine
        mock_engine = MagicMock()
        result = verify_columns(mock_engine)

        # Verify the result
        self.assertTrue(result)
        mock_inspector.get_columns.assert_called_once_with("users")

    @patch("sqlalchemy.inspect")
    def test_verify_columns_missing_columns(self, mock_inspect):
        """Test verifying columns when some required columns are missing."""
        # Mock inspect return value
        mock_inspector = MagicMock()
        mock_inspect.return_value = mock_inspector

        # Mock get_columns to return only some required columns
        mock_inspector.get_columns.return_value = [
            {"name": "id"},
            {"name": "email"},
            # Missing: username, first_name, last_name, facebook_oauth_id
        ]

        # Call function with mock engine
        mock_engine = MagicMock()
        result = verify_columns(mock_engine)

        # Verify the result
        self.assertFalse(result)
        mock_inspector.get_columns.assert_called_once_with("users")

    def test_check_user_data(self):
        """Test checking user data in the database."""
        # Create a mock engine and connection
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        # Mock the SQL query results
        mock_conn.execute.side_effect = [
            MagicMock(scalar=lambda: 10),  # Total users
            MagicMock(scalar=lambda: 8),  # Users with username
            MagicMock(scalar=lambda: 2),  # Users without username
            MagicMock(
                fetchall=lambda: [  # Sample users
                    (1, "user1@example.com", "user1"),
                    (2, "user2@example.com", "user2"),
                    (3, "user3@example.com", None),
                ]
            ),
        ]

        # Call the function
        users_with_username, users_without_username = check_user_data(mock_engine)

        # Check the results
        self.assertEqual(users_with_username, 8)
        self.assertEqual(users_without_username, 2)

        # Verify execute calls
        self.assertEqual(mock_conn.execute.call_count, 4)


if __name__ == "__main__":
    unittest.main()
