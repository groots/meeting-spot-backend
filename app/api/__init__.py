"""API blueprints for the application."""

import uuid
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_restx import Api

from .. import db
from ..models import ContactType, MeetingRequest, MeetingRequestStatus
from .auth import api as auth_ns
from .meeting_requests import api as meeting_requests_ns
from .users import api as users_ns

# Create API v1 blueprint
api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# Create API v2 blueprint
api_v2_bp = Blueprint("api_v2", __name__, url_prefix="/api/v2")

# Create a limiter instance
limiter = Limiter(key_func=get_remote_address)


# Add a test route directly to the blueprint
@api_v1_bp.route("/test/")
def test_route():
    return jsonify({"message": "API v1 test route working"})


# Create API v1 instance
api_v1 = Api(
    api_v1_bp,
    version="1.0",
    title="Find a Meeting Spot API v1",
    description="API v1 for finding meeting spots between two locations",
    doc="/docs",  # Always enable Swagger UI
    serve_challenge_on_401=True,
    default_mediatype="application/json",
    catch_all_404s=True,
)

# Create API v2 instance
api_v2 = Api(
    api_v2_bp,
    version="2.0",
    title="Find a Meeting Spot API v2",
    description="API v2 for finding meeting spots between two locations",
    doc="/docs",  # Always enable Swagger UI
    serve_challenge_on_401=True,
    default_mediatype="application/json",
    catch_all_404s=True,
)

# Register namespaces for v1
api_v1.add_namespace(auth_ns, path="/auth")
api_v1.add_namespace(meeting_requests_ns, path="/meeting-requests")
api_v1.add_namespace(users_ns, path="/users")

# Register namespaces for v2
api_v2.add_namespace(auth_ns, path="/auth")
api_v2.add_namespace(meeting_requests_ns, path="/meeting-requests")
api_v2.add_namespace(users_ns, path="/users")

# No need to import routes since we're using Flask-RESTX namespaces
