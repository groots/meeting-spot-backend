#!/usr/bin/env python
"""
Pre-deployment CORS Test Script

This script tests that CORS is correctly configured before deployment to GCP.
It simulates requests from different origins to ensure they are properly handled.

Usage:
    python test_cors_predeployment.py [--port PORT]

Prerequisites:
    - The Flask application must be running on localhost
    - The Cloud SQL Proxy should be running if database access is needed
"""

import argparse
import json
import os
import subprocess
import sys
import time
from urllib.parse import urlparse

import requests
from colorama import Fore, Style, init

# Initialize colorama for cross-platform colored terminal output
init()

# Configuration
DEFAULT_PORT = 8081
FLASK_APP = "wsgi.py"
TEST_TIMEOUT = 60  # seconds
ENDPOINTS = [
    "/debug/db-check",
    "/debug/health",
    "/api/v1/test/",
    "/api/v1/auth/register",  # Just for OPTIONS preflight testing
]

# Production origins to test
PROD_ORIGINS = [
    "https://findameetingspot.com",
    "https://www.findameetingspot.com",
    "https://find-a-meeting-spot.web.app",
    "https://find-a-meeting-spot.ue.r.appspot.com",
]


def print_success(msg):
    """Print a success message in green."""
    print(f"{Fore.GREEN}{msg}{Style.RESET_ALL}")


def print_error(msg):
    """Print an error message in red."""
    print(f"{Fore.RED}{msg}{Style.RESET_ALL}")


def print_info(msg):
    """Print an informational message in blue."""
    print(f"{Fore.BLUE}{msg}{Style.RESET_ALL}")


def print_warning(msg):
    """Print a warning message in yellow."""
    print(f"{Fore.YELLOW}{msg}{Style.RESET_ALL}")


def is_server_running(port):
    """Check if the server is already running on the specified port."""
    try:
        resp = requests.get(f"http://localhost:{port}/", timeout=2)
        return True
    except requests.RequestException:
        return False


def start_server(port):
    """Start the Flask server if it's not already running."""
    if is_server_running(port):
        print_info(f"Server already running on port {port}")
        return True

    print_info(f"Starting Flask server on port {port}...")
    try:
        # Force environment variables for testing
        env = os.environ.copy()
        env["FLASK_APP"] = FLASK_APP
        env["FLASK_DEBUG"] = "True"
        env["CORS_ORIGINS"] = ",".join(PROD_ORIGINS)

        # Start server in the background
        process = subprocess.Popen(
            ["python", "-m", "flask", "run", "--port", str(port)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Wait for server to start
        start_time = time.time()
        while not is_server_running(port):
            if time.time() - start_time > TEST_TIMEOUT:
                print_error(f"Server failed to start within {TEST_TIMEOUT} seconds")
                return False
            if process.poll() is not None:
                # Server process exited
                stdout, stderr = process.communicate()
                print_error("Server failed to start:")
                print(stderr.decode("utf-8"))
                return False
            time.sleep(0.5)

        print_success(f"Server started successfully on port {port}")
        return True
    except Exception as e:
        print_error(f"Error starting server: {e}")
        return False


def test_cors_preflight(endpoint, origin, port):
    """Test OPTIONS preflight requests with CORS headers."""
    url = f"http://localhost:{port}{endpoint}"

    headers = {
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Content-Type,Authorization",
    }

    try:
        response = requests.options(url, headers=headers, timeout=5)

        # Check for CORS headers
        cors_headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": None,  # Any value is acceptable
            "Access-Control-Allow-Headers": None,  # Any value is acceptable
        }

        success = True
        missing_headers = []

        for header, expected_value in cors_headers.items():
            if header not in response.headers:
                missing_headers.append(header)
                success = False
            elif expected_value is not None and response.headers[header] != expected_value:
                print_error(f"  - {header}: Expected '{expected_value}', got '{response.headers[header]}'")
                success = False

        if missing_headers:
            print_error(f"  - Missing CORS headers: {', '.join(missing_headers)}")

        if success:
            print_success(f"  ✓ OPTIONS {endpoint} from {origin} - CORS headers correct")
        else:
            print_error(f"  ✗ OPTIONS {endpoint} from {origin} - CORS headers incorrect")
            print_info("  Headers received:")
            for name, value in response.headers.items():
                print(f"  - {name}: {value}")

        return success

    except requests.RequestException as e:
        print_error(f"  ✗ OPTIONS {endpoint} from {origin} - Request failed: {e}")
        return False


def test_cors_actual_request(endpoint, origin, port):
    """Test actual GET/POST requests with CORS headers."""
    url = f"http://localhost:{port}{endpoint}"

    headers = {
        "Origin": origin,
        "Content-Type": "application/json",
    }

    method = "POST" if endpoint == "/api/v1/auth/register" else "GET"

    try:
        if method == "POST":
            # For registration endpoint, send test data
            data = {"email": f"test_{int(time.time())}@example.com", "password": "TestPassword123!"}
            response = requests.post(url, headers=headers, json=data, timeout=5)
        else:
            response = requests.get(url, headers=headers, timeout=5)

        # Check for CORS headers in the response
        success = "Access-Control-Allow-Origin" in response.headers
        status_ok = 200 <= response.status_code < 400  # Any success or redirect

        if success and status_ok:
            print_success(f"  ✓ {method} {endpoint} from {origin} - Status: {response.status_code}")
        elif not success:
            print_error(f"  ✗ {method} {endpoint} from {origin} - Missing CORS headers")
            print_info("  Headers received:")
            for name, value in response.headers.items():
                print(f"  - {name}: {value}")
        else:
            print_error(f"  ✗ {method} {endpoint} from {origin} - Status: {response.status_code}")
            try:
                print_info("  Response body:")
                print(json.dumps(response.json(), indent=2))
            except:
                print(response.text[:200] + "..." if len(response.text) > 200 else response.text)

        return success and status_ok

    except requests.RequestException as e:
        print_error(f"  ✗ {method} {endpoint} from {origin} - Request failed: {e}")
        return False


def run_cors_tests(port):
    """Run all CORS tests against the specified endpoints and origins."""
    results = {"preflight": [], "actual": []}

    print_info("\n=== Testing CORS Preflight Requests ===")
    for origin in PROD_ORIGINS:
        print_info(f"\nOrigin: {origin}")
        for endpoint in ENDPOINTS:
            result = test_cors_preflight(endpoint, origin, port)
            results["preflight"].append({"origin": origin, "endpoint": endpoint, "success": result})

    print_info("\n=== Testing Actual Requests with CORS ===")
    for origin in PROD_ORIGINS:
        print_info(f"\nOrigin: {origin}")
        for endpoint in ENDPOINTS:
            # Skip POST to register if we just want to test CORS
            if endpoint == "/api/v1/auth/register" and origin != PROD_ORIGINS[0]:
                continue

            result = test_cors_actual_request(endpoint, origin, port)
            results["actual"].append({"origin": origin, "endpoint": endpoint, "success": result})

    return results


def analyze_results(results):
    """Analyze test results and print a summary."""
    preflight_success = sum(1 for r in results["preflight"] if r["success"])
    preflight_total = len(results["preflight"])
    preflight_pct = (preflight_success / preflight_total) * 100 if preflight_total > 0 else 0

    actual_success = sum(1 for r in results["actual"] if r["success"])
    actual_total = len(results["actual"])
    actual_pct = (actual_success / actual_total) * 100 if actual_total > 0 else 0

    total_success = preflight_success + actual_success
    total_tests = preflight_total + actual_total
    total_pct = (total_success / total_tests) * 100 if total_tests > 0 else 0

    print_info("\n=== Test Results Summary ===")

    if preflight_pct == 100 and actual_pct == 100:
        print_success(f"✓ All tests passed! {total_success}/{total_tests} tests successful ({total_pct:.1f}%)")
        print_success("✓ CORS is correctly configured for all tested origins and endpoints")
        return True
    else:
        print_error(f"✗ Some tests failed: {total_success}/{total_tests} tests successful ({total_pct:.1f}%)")
        print_error(f"  - Preflight requests: {preflight_success}/{preflight_total} ({preflight_pct:.1f}%)")
        print_error(f"  - Actual requests: {actual_success}/{actual_total} ({actual_pct:.1f}%)")

        # Show failing endpoints by origin
        print_warning("\nFailing endpoints by origin:")
        all_results = results["preflight"] + results["actual"]
        for origin in PROD_ORIGINS:
            failing = [r["endpoint"] for r in all_results if r["origin"] == origin and not r["success"]]
            if failing:
                print_warning(f"  {origin}:")
                for endpoint in failing:
                    print_warning(f"    - {endpoint}")

        return False


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Test CORS configuration before deployment")
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help=f"Port to run the Flask server on (default: {DEFAULT_PORT})"
    )
    args = parser.parse_args()

    print_info("=== CORS Pre-deployment Test ===")
    print_info(f"Testing endpoints: {', '.join(ENDPOINTS)}")
    print_info(f"Testing origins: {', '.join(PROD_ORIGINS)}")

    server_running = is_server_running(args.port)
    if not server_running:
        server_started = start_server(args.port)
        if not server_started:
            print_error("Could not start server. Exiting.")
            return 1

    # Give the server a moment to fully initialize
    time.sleep(2)

    # Run the tests
    results = run_cors_tests(args.port)
    success = analyze_results(results)

    if success:
        print_success("\n✓ Your application is ready for deployment!")
        return 0
    else:
        print_error("\n✗ CORS issues detected! Please fix before deploying.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
