from typing import Any, Dict, List, Optional, Union

from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from .config import config

# This file makes the app directory a Python package


db = SQLAlchemy()
migrate = Migrate()


def create_app(config_name="default") -> None:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Configure CORS
    if app.debug:
        CORS(app, resources={r"/*": {"origins": "*"}})
    else:
        CORS(app, resources={r"/*": {"origins": app.config["CORS_ORIGINS"]}})

    # Import models to register them with SQLAlchemy
    from .models import MeetingRequest, MeetingRequestStatus, ContactType

    # Register API blueprints
    from .routes import api_bp as api_v2_bp
    from .api import api_bp as api_v1_bp

    app.register_blueprint(api_v2_bp, url_prefix="/api", name="api_v2")
    app.register_blueprint(api_v1_bp, url_prefix="/api/v1", name="api_v1")

    # Register error handlers
    from .errors import register_error_handlers

    register_error_handlers(app)

    return app
