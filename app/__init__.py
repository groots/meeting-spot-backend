"""Core application factory."""

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from .config import config
from .errors import register_error_handlers

# This file makes the app directory a Python package


db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


def create_app(config_name="default"):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Configure rate limiter with more lenient limits
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["1000 per day", "100 per hour"],
        storage_uri="memory://",
        strategy="fixed-window",  # Use fixed window strategy for more predictable behavior
    )

    # Configure CORS
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Register error handlers
    register_error_handlers(app)

    # Import and register blueprints
    from .api import api_v1_bp, api_v2_bp, debug_bp
    from .routes import api_bp

    # Register blueprints with correct prefixes
    app.register_blueprint(api_bp)  # This has the /api prefix
    app.register_blueprint(api_v1_bp)  # This has the /api/v1 prefix
    app.register_blueprint(api_v2_bp)  # This has the /api/v2 prefix
    app.register_blueprint(debug_bp)  # Register debug endpoints

    return app
