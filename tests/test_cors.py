"""Tests for CORS configuration."""
import pytest
import requests


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


def test_cors_production_register(client, monkeypatch):
    """Test CORS configuration for production register endpoint."""
    # Mock production config
    monkeypatch.setitem(client.application.config, "CORS_ORIGINS", ["https://findameetingspot.com"])

    headers = {
        "Origin": "https://findameetingspot.com",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Referer": "https://findameetingspot.com/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
    }

    # Test OPTIONS (preflight)
    options_response = client.options(
        "/api/v1/auth/register",
        headers={
            **headers,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,accept",
        },
    )

    assert options_response.status_code == 200, "Preflight request failed"
    assert "Access-Control-Allow-Origin" in options_response.headers, "Missing CORS allow origin header"
    assert (
        options_response.headers["Access-Control-Allow-Origin"] == "https://findameetingspot.com"
    ), "Wrong origin allowed"
    assert "Access-Control-Allow-Methods" in options_response.headers, "Missing allowed methods"
    assert "POST" in options_response.headers["Access-Control-Allow-Methods"], "POST not in allowed methods"
    assert "Access-Control-Allow-Headers" in options_response.headers, "Missing allowed headers"
    assert all(
        header.lower() in options_response.headers["Access-Control-Allow-Headers"].lower()
        for header in ["Content-Type", "Accept"]
    ), "Required headers not allowed"


def test_cors_production_origins(client, monkeypatch):
    """Test CORS with all production origins."""
    production_origins = [
        "https://findameetingspot.com",
        "https://www.findameetingspot.com",
        "https://find-a-meeting-spot.web.app",
        "https://find-a-meeting-spot.ue.r.appspot.com",
    ]

    # Mock production config
    monkeypatch.setitem(client.application.config, "CORS_ORIGINS", production_origins)

    for origin in production_origins:
        headers = {"Origin": origin, "Accept": "application/json", "Content-Type": "application/json"}

        # Test preflight
        options_response = client.options(
            "/api/v1/auth/register",
            headers={
                **headers,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,accept",
            },
        )

        assert options_response.status_code == 200, f"Preflight failed for {origin}"
        assert options_response.headers["Access-Control-Allow-Origin"] == origin, f"Wrong origin allowed for {origin}"
