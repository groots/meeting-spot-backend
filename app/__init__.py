"""Flask application factory."""
import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, current_app, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()


def setup_logging(app):
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    try:
        os.makedirs("logs")
    except FileExistsError:
        pass  # Directory already exists

    # Set up file handler for CORS logs
    cors_handler = RotatingFileHandler("logs/cors.log", maxBytes=10000000, backupCount=5)
    cors_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s"))
    cors_handler.setLevel(logging.INFO)

    # Create CORS logger
    cors_logger = logging.getLogger("cors")
    cors_logger.setLevel(logging.INFO)
    cors_logger.addHandler(cors_handler)

    # Set up file handler for general application logs
    handler = RotatingFileHandler("logs/app.log", maxBytes=10000000, backupCount=5)
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s"))
    handler.setLevel(logging.INFO)

    # Add handlers to app logger
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info("Application startup")


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

    # Set up logging
    setup_logging(app)

    # Initialize CORS with app-wide settings
    CORS(
        app,
        resources={
            r"/*": {
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

    # Add security headers middleware
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses."""
        cors_logger = logging.getLogger("cors")

        # Log request details
        cors_logger.info(
            "Request: %s %s\nHeaders: %s\nOrigin: %s\n",
            request.method,
            request.path,
            dict(request.headers),
            request.headers.get("Origin"),
        )

        # Add security headers
        if app.config.get("SECURITY_HEADERS"):
            for header, value in app.config["SECURITY_HEADERS"].items():
                response.headers[header] = value

        # For OPTIONS requests, ensure CORS headers are present and return 200
        if request.method == "OPTIONS":
            response.status_code = 200
            # Ensure CORS headers are present
            if "Origin" in request.headers:
                origin = request.headers["Origin"]
                allowed_origins = app.config.get("CORS_ORIGINS", [])

                # Log CORS validation
                cors_logger.info(
                    "CORS Validation:\nOrigin: %s\nAllowed Origins: %s\nRequest Headers: %s\n",
                    origin,
                    allowed_origins,
                    request.headers.get("Access-Control-Request-Headers"),
                )

                if origin in allowed_origins:
                    response.headers["Access-Control-Allow-Origin"] = origin
                    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                    response.headers[
                        "Access-Control-Allow-Headers"
                    ] = "Content-Type, Authorization, Accept, X-Requested-With, Origin"
                    response.headers["Access-Control-Allow-Credentials"] = "true"
                    response.headers["Access-Control-Max-Age"] = "3600"

                    cors_logger.info("CORS headers set successfully for origin: %s", origin)
                else:
                    cors_logger.warning("Invalid origin attempted access: %s", origin)

        # Log response details
        cors_logger.info("Response:\nStatus: %s\nHeaders: %s\n", response.status_code, dict(response.headers))

        return response

    # Add error handlers
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error("Server Error: %s", error)
        return jsonify(error="Internal server error"), 500

    @app.errorhandler(503)
    def service_unavailable(error):
        app.logger.error("Service Unavailable: %s", error)
        return jsonify(error="Service temporarily unavailable"), 503

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
