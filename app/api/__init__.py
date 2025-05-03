"""API blueprint registration."""

from flask import Blueprint

api = Blueprint("api", __name__)

# Import blueprints
from .auth import auth_bp
from .meeting_requests import meeting_requests_bp

# Register blueprints
api.register_blueprint(auth_bp, url_prefix="/auth")
api.register_blueprint(meeting_requests_bp, url_prefix="/meeting-requests")

# Import any other routes after all blueprints are registered
# This is for routes that are registered directly on the api blueprint
