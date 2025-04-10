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
    response = client.options("/api/v1/cors-test", headers=headers)
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"


def test_cors_actual_requests(client):
    """Test actual CORS requests."""
    headers = {
        "Origin": "http://localhost:3000",
    }

    response = client.get("/api/v1/cors-test", headers=headers)
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert response.json == {"message": "CORS test successful"}


def test_cors_invalid_origin(client):
    """Test CORS with invalid origin."""
    headers = {
        "Origin": "http://malicious-site.com",
    }

    response = client.get("/api/v1/cors-test", headers=headers)
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers
