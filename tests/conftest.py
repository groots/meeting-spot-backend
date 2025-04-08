"""Test configuration and fixtures."""

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import inspect
from sqlalchemy.pool import StaticPool

from app import create_app, db
from app.models import ContactType, MeetingRequest, MeetingRequestStatus, User


@pytest.fixture(scope="session")
def test_key() -> bytes:
    """Generate a test encryption key."""
    return Fernet.generate_key()


@pytest.fixture(scope="session")
def app(test_key) -> None:
    """Create and configure a new app instance for each test."""
    # Set up test environment variables
    os.environ["ENCRYPTION_KEY"] = test_key.decode()
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key"
    # Force SQLite for testing
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    app = create_app("testing")  # Use testing config

    # Configure SQLite to use in-memory database
    app.config.update(
        {
            "ENCRYPTION_KEY": test_key.decode(),  # Store as string in config
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "SQLALCHEMY_ENGINE_OPTIONS": {
                "poolclass": StaticPool,
                "connect_args": {"check_same_thread": False},
            },
            "TESTING": True,
        }
    )

    # Push an application context
    ctx = app.app_context()
    ctx.push()

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


@pytest.fixture(autouse=True)
def _session(app) -> None:
    """Create a new database session for a test."""
    connection = db.engine.connect()
    transaction = connection.begin()

    # Create a session bound to this connection
    session = db.create_scoped_session(options={"bind": connection, "binds": {}})

    # Make this session the current one
    db.session = session

    yield session

    # Clean up
    session.close()
    transaction.rollback()
    connection.close()

    # Restore the original session
    db.session = db.create_scoped_session()


@pytest.fixture
def client(app) -> None:
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture
def test_user(_session) -> None:
    """Create a test user."""
    test_id = uuid.uuid4()
    user = User(
        id=test_id,
        email="test@example.com",
        password_hash="test-hash",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    _session.add(user)
    _session.commit()

    # Verify the user was created correctly
    queried_user = User.query.get(test_id)
    assert queried_user is not None
    assert queried_user.id == test_id

    return user


@pytest.fixture
def test_meeting_request(_session, test_user) -> None:
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
        token_b=uuid.uuid4().hex,
        status=MeetingRequestStatus.PENDING_B_ADDRESS,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    _session.add(request)
    _session.commit()

    # Verify the request was created correctly
    queried_request = MeetingRequest.query.get(request_id)
    assert queried_request is not None
    assert queried_request.request_id == request_id

    return request
