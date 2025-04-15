"""Flask application factory."""
import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, current_app, jsonify, request
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# IMPORTANT: Import CORS setup early
from .cors_middleware import setup_cors

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
    cors_logger.handlers = []  # Clear existing handlers if any
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
        config_name (str): The name of the configuration to use.

    Returns:
        Flask: The configured Flask application.
    """
    app = Flask(__name__)

    # Load config
    env = os.getenv("FLASK_ENV", config_name)
    app.logger.info(f"Using environment: {env}")

    if env == "production":
        app.config.from_object("app.config.ProductionConfig")
    elif env == "development":
        try:
            # First try to load from development_config.py (preferred for local dev)
            from development_config import DevelopmentConfig

            app.config.from_object(DevelopmentConfig)
            app.logger.info("Using development_config.py")
        except (ImportError, ModuleNotFoundError):
            # Fall back to the built-in config
            app.config.from_object("app.config.DevelopmentConfig")
            app.logger.info("Using app.config.DevelopmentConfig")
    elif env == "testing":
        app.config.from_object("app.config.TestingConfig")
    else:
        app.config.from_object("app.config.Config")

    # Override config with environment variables
    if hasattr(app.config, "from_prefixed_env"):
        app.config.from_prefixed_env("FLASK_")

    # Process CORS_ORIGINS from environment if present
    cors_origins_env = os.getenv("CORS_ORIGINS")
    if cors_origins_env:
        cors_origins = [origin.strip() for origin in cors_origins_env.split(",")]
        app.config["CORS_ORIGINS"] = cors_origins
        app.logger.info(f"Loaded CORS origins from environment: {cors_origins}")

    # Explicitly add important production origins if not present
    production_origins = [
        "https://findameetingspot.com",
        "https://www.findameetingspot.com",
        "https://find-a-meeting-spot.web.app",
        "https://find-a-meeting-spot.firebaseapp.com",
    ]

    if "CORS_ORIGINS" in app.config:
        for origin in production_origins:
            if origin not in app.config["CORS_ORIGINS"]:
                app.config["CORS_ORIGINS"].append(origin)
                app.logger.info(f"Added important production origin: {origin}")

    # Log the configured CORS origins for debugging
    app.logger.info(f"Configured CORS origins: {app.config.get('CORS_ORIGINS', [])}")

    # Set up logging
    setup_logging(app)

    # *** IMPORTANT: Set up CORS with our simplified middleware BEFORE other extensions and blueprints ***
    setup_cors(app)

    # Initialize database and other extensions AFTER CORS
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    # Add a root route handler for the welcome page
    @app.route("/")
    def index():
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Find A Meeting Spot API</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }
                h1 {
                    color: #3498db;
                    border-bottom: 2px solid #f1f1f1;
                    padding-bottom: 10px;
                }
                .container {
                    background-color: #fff;
                    border-radius: 5px;
                    padding: 20px;
                    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                }
                code {
                    background-color: #f8f9fa;
                    padding: 2px 5px;
                    border-radius: 3px;
                    font-family: 'Courier New', Courier, monospace;
                }
                ul {
                    margin-top: 20px;
                }
                li {
                    margin-bottom: 10px;
                }
                .footer {
                    margin-top: 30px;
                    text-align: center;
                    font-size: 0.9em;
                    color: #666;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Find A Meeting Spot API</h1>
                <p>Welcome to the Find A Meeting Spot API service! This is the backend server that powers the Find A Meeting Spot application.</p>

                <h2>API Endpoints</h2>
                <p>The API endpoints are available under the following paths:</p>
                <ul>
                    <li><code>/api/v1/...</code> - API version 1 endpoints</li>
                    <li><code>/api/v2/...</code> - API version 2 endpoints</li>
                    <li><code>/debug/...</code> - Debug and monitoring endpoints</li>
                </ul>

                <h2>Documentation</h2>
                <p>For detailed API documentation, please visit <a href="https://findameetingspot.com">Find A Meeting Spot</a> website.</p>

                <div class="footer">
                    <p>&copy; 2025 Find A Meeting Spot</p>
                </div>
            </div>
        </body>
        </html>
        """

    # Add CORS check route to easily test CORS configuration
    @app.route("/debug/cors-check")
    def cors_check():
        """Endpoint to check CORS configuration."""
        origin = request.headers.get("Origin", "No origin provided")
        cors_logger = logging.getLogger("cors")
        cors_logger.info(f"CORS check requested from origin: {origin}")

        allowed_origins = app.config.get("CORS_ORIGINS", [])
        is_allowed = origin in allowed_origins or "*" in allowed_origins

        return jsonify(
            {
                "origin": origin,
                "is_allowed": is_allowed,
                "allowed_origins": allowed_origins,
                "debug_mode": app.config.get("DEBUG", False),
                "environment": app.config.get("ENV", "unknown"),
            }
        )

    # Log all requests
    @app.before_request
    def log_request():
        """Log request details."""
        cors_logger = logging.getLogger("cors")
        cors_logger.info(
            "Request: %s %s\nHeaders: %s\nOrigin: %s\n",
            request.method,
            request.path,
            dict(request.headers),
            request.headers.get("Origin"),
        )

    # Add security headers middleware
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses."""
        cors_logger = logging.getLogger("cors")

        # Add security headers
        if app.config.get("SECURITY_HEADERS"):
            for header, value in app.config["SECURITY_HEADERS"].items():
                response.headers[header] = value

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

    with app.app_context():
        # Register API blueprints
        from app.api import init_app as init_api

        init_api(app)

        # Create database tables
        # db.create_all()

    return app
