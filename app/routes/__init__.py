# This file makes the routes directory a Python package

from flask import Blueprint, jsonify

api_bp = Blueprint("api", __name__)


@api_bp.route("/health")
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"})


__all__ = ["api_bp"]
