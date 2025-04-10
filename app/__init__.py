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

    # Configure CORS settings directly on the app
    app.config["CORS_ORIGINS"] = app.config.get("CORS_ORIGINS", ["http://localhost:3000"])
    app.config["CORS_ALLOW_HEADERS"] = [
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
    ]
    app.config["CORS_EXPOSE_HEADERS"] = [
        "Content-Type",
        "Authorization",
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Credentials",
        "Access-Control-Allow-Headers",
        "Access-Control-Allow-Methods",
    ]
    app.config["CORS_SUPPORTS_CREDENTIALS"] = True
    app.config["CORS_MAX_AGE"] = 3600
    app.config["CORS_SEND_WILDCARD"] = False
    app.config["CORS_AUTOMATIC_OPTIONS"] = True
    app.config["CORS_VARY_HEADER"] = True

    # Initialize CORS with app-wide settings
    CORS(app)

    # Add security headers middleware
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses."""
        # Add security headers
        if app.config.get("SECURITY_HEADERS"):
            for header, value in app.config["SECURITY_HEADERS"].items():
                response.headers[header] = value

        # Ensure OPTIONS requests return 200
        if request.method == "OPTIONS":
            response.status_code = 200

        return response

    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        # Register API blueprints
        from app.api import init_app as init_api

        init_api(app)

        # Create database tables
        db.create_all()

    return app
