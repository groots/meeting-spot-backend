"""Tests for CORS configuration."""
import pytest


def test_cors_preflight(client):
    """Test CORS preflight requests."""
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    }

    # Test registration endpoint
    response = client.options("/api/v1/auth/register", headers=headers)
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert response.headers["Access-Control-Allow-Methods"] == "GET, POST, PUT, DELETE, OPTIONS"
    assert "Content-Type" in response.headers["Access-Control-Allow-Headers"]

    # Test Google callback endpoint
    response = client.options("/api/v1/auth/google/callback", headers=headers)
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"

    # Test CORS test endpoint
    response = client.options("/api/v1/cors", headers=headers)
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"


def test_cors_actual_requests(client):
    """Test actual CORS requests."""
    headers = {
        "Origin": "http://localhost:3000",
    }

    response = client.get("/api/v1/cors", headers=headers)
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert response.json == {"message": "CORS test successful"}


def test_cors_invalid_origin(client):
    """Test CORS with invalid origin."""
    headers = {
        "Origin": "http://malicious-site.com",
    }

    response = client.get("/api/v1/cors", headers=headers)
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers


def test_cors_preflight_with_custom_headers(client):
    """Test CORS preflight with custom headers."""
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type, Authorization, X-Requested-With",
    }

    response = client.options("/api/v1/auth/register", headers=headers)
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert "Authorization" in response.headers["Access-Control-Allow-Headers"]
    assert "X-Requested-With" in response.headers["Access-Control-Allow-Headers"]
    assert response.headers["Access-Control-Allow-Credentials"] == "true"
    assert "3600" in response.headers["Access-Control-Max-Age"]


def test_cors_all_allowed_methods(client):
    """Test CORS preflight for all allowed HTTP methods."""
    methods = ["GET", "POST", "PUT", "DELETE"]

    for method in methods:
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "Content-Type",
        }

        response = client.options("/api/v1/cors", headers=headers)
        assert response.status_code == 200
        assert method in response.headers["Access-Control-Allow-Methods"]


def test_cors_with_credentials(client):
    """Test CORS requests with credentials."""
    headers = {
        "Origin": "http://localhost:3000",
        "Cookie": "dummy=value",
    }

    response = client.get("/api/v1/cors", headers=headers)
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert response.headers["Access-Control-Allow-Credentials"] == "true"


def test_cors_expose_headers(client):
    """Test CORS expose headers configuration."""
    headers = {
        "Origin": "http://localhost:3000",
    }

    response = client.get("/api/v1/cors", headers=headers)
    assert response.status_code == 200
    assert "Content-Type" in response.headers["Access-Control-Expose-Headers"]
    assert "Authorization" in response.headers["Access-Control-Expose-Headers"]
