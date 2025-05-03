"""API blueprint registration."""

from flask import Blueprint

api = Blueprint("api", __name__)

# Import and register blueprints
from .auth import auth_bp

api.register_blueprint(auth_bp, url_prefix="/auth")

# Import other routes after the Blueprint is defined
from . import meeting_requests
