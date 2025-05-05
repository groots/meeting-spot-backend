"""CORS test endpoint."""
from flask import Blueprint, current_app, jsonify
from flask_cors import CORS
from flask_restx import Namespace, Resource

cors_ns = Namespace("cors-test", description="CORS test operations")


@cors_ns.route("")
class CORSTestResource(Resource):
    def get(self):
        """Test endpoint for CORS."""
        return {"message": "CORS test successful"}

    def options(self):
        """Handle OPTIONS requests for CORS preflight."""
        return "", 200


def configure_cors(app):
    """Configure CORS for the application."""
    # Get allowed origins from configuration
    cors_origins = app.config.get(
        "CORS_ORIGINS",
        [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:5000",
            "http://localhost:5001",
            "http://localhost:8080",
            "http://localhost:8081",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080",
            "http://127.0.0.1:8081",
            "https://find-a-meeting-spot.web.app",
            "https://find-a-meeting-spot.ue.r.appspot.com",
            "https://findameetingspot.com",
            "https://www.findameetingspot.com",
            "https://find-a-meeting-spot.firebaseapp.com",
        ],
    )

    current_app.logger.info(f"Initializing CORS with allowed origins: {cors_origins}")

    # Configure CORS
    CORS(
        app,
        resources={r"/api/*": {"origins": cors_origins, "supports_credentials": True}},
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )
