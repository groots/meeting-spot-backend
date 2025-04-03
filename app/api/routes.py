"""API routes for the application."""

from flask import jsonify

from . import api_v2_bp


@api_v2_bp.route("/health")
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200
