"""Test configuration and fixtures."""

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import inspect, text
from sqlalchemy.pool import StaticPool

from app import create_app, db
from app.models import ContactType, MeetingRequest, MeetingRequestStatus, User


@pytest.fixture(scope="session")
def test_key() -> bytes:
    """Generate a test encryption key."""
    return Fernet.generate_key()


@pytest.fixture(scope="session")
def app() -> None:
    """Create a Flask app for testing."""
    # Set up the test database URI
    TEST_DATABASE_URL = os.environ.get(
        "TEST_DATABASE_URL", "sqlite:///:memory:"
    )  # Use in-memory SQLite if no URL provided

    app = create_app(
        {
            "TESTING": True,  # Explicitly set TESTING to True
            "DEBUG": False,
            "SQLALCHEMY_DATABASE_URI": TEST_DATABASE_URL,
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "SECRET_KEY": "test-key",
            "ENCRYPTION_KEY": os.environ.get("ENCRYPTION_KEY", "test-encryption-key"),
            "JWT_SECRET_KEY": "test-jwt-secret-key",
            "GOOGLE_MAPS_API_KEY": "test-maps-api-key",
            "SERVER_NAME": "localhost:5000",
            "APPLICATION_ROOT": "/",
            "PREFERRED_URL_SCHEME": "http",
        }
    )

    # Push an application context that will be used for the entire test session
    ctx = app.app_context()
    ctx.push()

    # Verify encryption key is set
    if not app.config.get("ENCRYPTION_KEY"):
        raise ValueError("Encryption key not set in app config")
    print(f"\nEncryption key is set: {bool(app.config['ENCRYPTION_KEY'])}")  # Debug print

    # Drop all tables first to ensure a clean state
    db.drop_all()

    # Create all tables
    db.create_all()

    # Verify tables exist
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"\nCreated tables: {tables}")  # Debug print

    # Verify specific tables exist
    required_tables = {"users", "meeting_requests"}
    missing_tables = required_tables - set(tables)
    if missing_tables:
        raise Exception(f"Missing required tables: {missing_tables}")

    # Verify table structure
    for table in required_tables:
        columns = {col["name"] for col in inspector.get_columns(table)}
        print(f"\nColumns in {table}: {columns}")  # Debug print

    yield app

    # Clean up
    db.session.remove()
    db.drop_all()
    ctx.pop()


@pytest.fixture(scope="function")
def app_context(app):
    """Create a new application context for each test."""
    with app.app_context():
        # Ensure encryption key is set in current app context
        from flask import current_app

        if not current_app.config.get("ENCRYPTION_KEY"):
            current_app.config["ENCRYPTION_KEY"] = os.environ["ENCRYPTION_KEY"]
        yield


@pytest.fixture(autouse=True)
def _session(app) -> None:
    """Create a new database session for a test."""
    # Connect to the database and begin a transaction
    connection = db.engine.connect()
    transaction = connection.begin()

    # Begin a nested transaction (using SAVEPOINT)
    session = db.session
    session.begin_nested()

    # Patch the commit method to use flush instead
    old_commit = session.commit
    session.commit = session.flush

    yield session

    # Restore commit method
    session.commit = old_commit

    # Rollback the transaction and close the connection
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(app) -> None:
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture
def test_user(app_context, db_session) -> None:
    """Create a test user."""
    test_id = uuid.uuid4()
    user = User(
        id=test_id,
        email="test@example.com",
        password_hash="test-hash",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    db_session.commit()

    # Verify the user was created correctly
    queried_user = User.query.get(test_id)
    assert queried_user is not None
    assert queried_user.id == test_id

    return user


@pytest.fixture
def test_meeting_request(app_context, test_user, db_session) -> None:
    """Create a test meeting request."""
    request_id = uuid.uuid4()
    request = MeetingRequest(
        request_id=request_id,
        user_a_id=test_user.id,
        address_a_lat=37.7749,
        address_a_lon=-122.4194,
        location_type="cafe",
        user_b_contact_type=ContactType.EMAIL,
        user_b_contact="test@example.com",  # Use the property to handle encryption
        user_b_email="test@example.com",  # Add this field for contact creation
        location_a={"address": "123 Test St, San Francisco, CA", "latitude": 37.7749, "longitude": -122.4194},
        token_b=uuid.uuid4().hex,
        status=MeetingRequestStatus.PENDING_B_ADDRESS,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(request)
    db_session.commit()

    # Verify the request was created correctly
    queried_request = MeetingRequest.query.get(request_id)
    assert queried_request is not None
    assert queried_request.request_id == request_id

    return request


@pytest.fixture(scope="function")
def auth_headers(app_context, test_user, app):
    """Create authentication headers with JWT token."""
    from flask_jwt_extended import create_access_token

    access_token = create_access_token(identity=test_user.id)
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture(scope="function")
def mock_process_meeting_request():
    """Mock the process_meeting_request function to always succeed."""
    from unittest.mock import patch

    from app.models.enums import MeetingRequestStatus

    with patch("app.utils.location.process_meeting_request") as mock_process:
        # Set up the mock to update the status and return True
        def side_effect(meeting_request):
            meeting_request.status = MeetingRequestStatus.CALCULATING
            meeting_request.suggested_options = [
                {
                    "name": "Test Restaurant",
                    "place_id": "place123",
                    "address": "123 Test St, Test City",
                    "location": {"lat": 37.78, "lng": -122.41},
                    "rating": 4.5,
                    "photos": ["https://example.com/photo.jpg"],
                }
            ]
            return True

        mock_process.side_effect = side_effect
        yield mock_process


@pytest.fixture
def db_session(app):
    """Create a separate testing session per function.
    This allows us to commit data without affecting other tests.
    """
    with app.app_context():
        # Connect to the database and create a new transaction
        connection = db.engine.connect()
        transaction = connection.begin()

        # Bind a new session to the transaction
        # options={"bind": connection, "binds": {}}
        session = db.session.registry()
        db.session.configure(bind=connection)

        # Return the session
        yield db.session

        # Clean up the session
        db.session.remove()
        transaction.rollback()
        connection.close()
