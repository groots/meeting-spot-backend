#!/usr/bin/env python
"""
Deployed API CORS Test Script

This script tests that CORS is correctly configured on a deployed API.
It simulates requests from different origins to ensure they are properly handled.

Usage:
    python test_cors_deployed.py [--api-url API_URL]

Example:
    python test_cors_deployed.py --api-url https://api.findameetingspot.com
"""

import argparse
import json
import sys
import time
from urllib.parse import urljoin

import requests
from colorama import Fore, Style, init

# Initialize colorama for cross-platform colored terminal output
init()

# Configuration
DEFAULT_API_URL = "https://api.findameetingspot.com"
ENDPOINTS = [
    "/debug/db-check",
    "/debug/health",
    "/api/v1/test/",
    # Include other critical endpoints you want to test
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


def test_cors_preflight(endpoint, origin, api_url):
    """Test OPTIONS preflight requests with CORS headers."""
    url = urljoin(api_url, endpoint.lstrip("/"))

    headers = {
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Content-Type,Authorization",
    }

    try:
        response = requests.options(url, headers=headers, timeout=10)

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


def test_cors_actual_request(endpoint, origin, api_url):
    """Test actual GET requests with CORS headers."""
    url = urljoin(api_url, endpoint.lstrip("/"))

    headers = {
        "Origin": origin,
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)

        # Check for CORS headers in the response
        success = "Access-Control-Allow-Origin" in response.headers
        status_ok = 200 <= response.status_code < 400  # Any success or redirect

        if success and status_ok:
            print_success(f"  ✓ GET {endpoint} from {origin} - Status: {response.status_code}")
        elif not success:
            print_error(f"  ✗ GET {endpoint} from {origin} - Missing CORS headers")
            print_info("  Headers received:")
            for name, value in response.headers.items():
                print(f"  - {name}: {value}")
        else:
            print_error(f"  ✗ GET {endpoint} from {origin} - Status: {response.status_code}")
            try:
                print_info("  Response body:")
                print(json.dumps(response.json(), indent=2))
            except:
                print(response.text[:200] + "..." if len(response.text) > 200 else response.text)

        return success and status_ok

    except requests.RequestException as e:
        print_error(f"  ✗ GET {endpoint} from {origin} - Request failed: {e}")
        return False


def run_cors_tests(api_url):
    """Run all CORS tests against the specified endpoints and origins."""
    results = {"preflight": [], "actual": []}

    print_info("\n=== Testing CORS Preflight Requests ===")
    for origin in PROD_ORIGINS:
        print_info(f"\nOrigin: {origin}")
        for endpoint in ENDPOINTS:
            result = test_cors_preflight(endpoint, origin, api_url)
            results["preflight"].append({"origin": origin, "endpoint": endpoint, "success": result})

    print_info("\n=== Testing Actual Requests with CORS ===")
    for origin in PROD_ORIGINS:
        print_info(f"\nOrigin: {origin}")
        for endpoint in ENDPOINTS:
            result = test_cors_actual_request(endpoint, origin, api_url)
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
    parser = argparse.ArgumentParser(description="Test CORS configuration on deployed API")
    parser.add_argument(
        "--api-url", type=str, default=DEFAULT_API_URL, help=f"Base URL of the API to test (default: {DEFAULT_API_URL})"
    )
    args = parser.parse_args()

    print_info("=== CORS Deployed API Test ===")
    print_info(f"API URL: {args.api_url}")
    print_info(f"Testing endpoints: {', '.join(ENDPOINTS)}")
    print_info(f"Testing origins: {', '.join(PROD_ORIGINS)}")

    # Run the tests
    results = run_cors_tests(args.api_url)
    success = analyze_results(results)

    if success:
        print_success("\n✓ Your deployed API CORS configuration is correct!")
        return 0
    else:
        print_error("\n✗ CORS issues detected in your deployed API!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
