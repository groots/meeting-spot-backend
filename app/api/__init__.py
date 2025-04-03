
from flask import Blueprint
from flask_restx import Api

from .auth import api as auth_ns
from .meeting_requests import api as meeting_requests_ns
from .users import api as users_ns

# Create Blueprint
api_bp = Blueprint("api_v1", __name__)

# Create API instance
api = Api(
    api_bp,
    version="1.0",
    title="Find a Meeting Spot API",
    description="API for finding meeting spots between two locations",
    doc="/docs",  # Always enable Swagger UI
    serve_challenge_on_401=True,
    default_mediatype="application/json",
    catch_all_404s=True,
)

# Register namespaces
api.add_namespace(auth_ns, path="/auth")
api.add_namespace(meeting_requests_ns, path="/meeting-requests")
api.add_namespace(users_ns, path="/users")
