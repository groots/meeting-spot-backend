# This file makes the routes directory a Python package

from flask import Blueprint, jsonify

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/health")
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"})


@api_bp.route("/debug/routes")
def list_routes():
    """Debug endpoint to list all registered routes."""
    from flask import current_app

    routes = []
    for rule in current_app.url_map.iter_rules():
        routes.append({"endpoint": rule.endpoint, "methods": list(rule.methods), "path": str(rule)})
    return jsonify(routes)


__all__ = ["api_bp"]
