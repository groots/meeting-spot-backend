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

# Import encryption key middleware
from .middleware import register_middleware

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

    # Disable automatic redirects for trailing slashes
    app.url_map.strict_slashes = False

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

    # Google OAuth settings
    app.config["GOOGLE_CLIENT_ID"] = os.getenv("GOOGLE_CLIENT_ID", "")

    # Facebook OAuth settings
    app.config["FACEBOOK_APP_ID"] = os.getenv("FACEBOOK_APP_ID", "")

    # Configure rate limiting
    app.config["RATELIMIT_DEFAULT"] = "100 per minute"

    # Set up logging
    setup_logging(app)

    # *** IMPORTANT: Set up CORS with our simplified middleware BEFORE other extensions and blueprints ***
    setup_cors(app)

    # Register encryption key middleware
    register_middleware(app)

    # Initialize database and other extensions AFTER CORS
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    # Create necessary directories
    create_storage_directories(app)

    # Import and register blueprints
    from app.api import api as api_blueprint

    app.register_blueprint(api_blueprint, url_prefix="/api/v1")

    # Add a root route for health checks
    @app.route("/")
    def index():
        return jsonify({"status": "ok", "message": "Find A Meeting Spot API is running"})

    # Add error handlers
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal error: {error}")
        return jsonify({"error": "Internal server error"}), 500

    return app


def create_storage_directories(app):
    """Create necessary storage directories for the application."""
    # Create instance directory if it doesn't exist
    os.makedirs(os.path.join(app.instance_path), exist_ok=True)

    # Create profile pictures directory if it doesn't exist
    profile_pictures_dir = os.path.join(app.instance_path, "profile_pictures")
    os.makedirs(profile_pictures_dir, exist_ok=True)

    app.logger.info(f"Storage directories created: {profile_pictures_dir}")
