"""Flask application factory."""
import os

from flask import Flask, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()


def create_app(config_name="development"):
    """Create and configure the Flask application.

    Args:
        config_name: The name of the configuration to use.

    Returns:
        The configured Flask application.
    """
    app = Flask(__name__)

    # Load configuration based on environment
    if config_name == "testing":
        app.config.from_object("config.TestingConfig")
    elif config_name == "development":
        # Use our development config that doesn't require Google Cloud
        from development_config import DevelopmentConfig

        app.config.from_object(DevelopmentConfig)
    else:
        app.config.from_object("config.Config")

    # Override config with environment variables
    app.config.from_envvar("APP_CONFIG", silent=True)

    # Initialize extensions with CORS configuration
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": app.config.get("CORS_ORIGINS", ["http://localhost:3000"]),
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": [
                    "Content-Type",
                    "Authorization",
                    "Accept",
                    "X-Requested-With",
                    "Origin",
                    "Access-Control-Request-Method",
                    "Access-Control-Request-Headers",
                    "Referer",
                    "User-Agent",
                    "Sec-Fetch-Mode",
                    "Sec-Fetch-Site",
                    "Sec-Fetch-Dest",
                    "sec-ch-ua",
                    "sec-ch-ua-mobile",
                    "sec-ch-ua-platform",
                ],
                "expose_headers": [
                    "Content-Type",
                    "Authorization",
                    "Access-Control-Allow-Origin",
                    "Access-Control-Allow-Credentials",
                    "Access-Control-Allow-Headers",
                    "Access-Control-Allow-Methods",
                ],
                "supports_credentials": True,
                "max_age": 3600,
                "send_wildcard": False,
                "automatic_options": True,
                "vary_header": True,
            }
        },
    )

    # Add CORS headers middleware
    @app.after_request
    def after_request(response):
        """Add CORS headers to all responses."""
        # Get the origin from the request
        origin = request.headers.get("Origin")

        # If the origin is in our allowed origins, set it in the response
        if origin and origin in app.config.get("CORS_ORIGINS", []):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers[
                "Access-Control-Allow-Headers"
            ] = "Content-Type, Authorization, Accept, X-Requested-With, Origin, Referer, User-Agent, sec-ch-ua, sec-ch-ua-mobile, sec-ch-ua-platform"
            response.headers["Access-Control-Max-Age"] = "3600"

        return response

    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    # Add security headers middleware
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses."""
        if app.config.get("SECURITY_HEADERS"):
            for header, value in app.config["SECURITY_HEADERS"].items():
                response.headers[header] = value
        return response

    with app.app_context():
        # Register API blueprints
        from app.api import init_app as init_api

        init_api(app)

        # Create database tables
        db.create_all()

    return app
