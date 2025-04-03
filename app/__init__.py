"""Core application factory."""

from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from .config import config

# This file makes the app directory a Python package


db = SQLAlchemy()
migrate = Migrate()


def create_app(config_name="default"):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Configure CORS
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Import and register blueprints
    from .api import api_v1_bp, api_v2_bp
    from .routes import api_bp

    app.register_blueprint(api_v1_bp)
    app.register_blueprint(api_v2_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app
