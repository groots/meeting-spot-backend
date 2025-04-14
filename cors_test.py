#!/usr/bin/env python3
"""
Simple script to test CORS headers from the deployed API endpoint.
"""

import requests
from colorama import Fore, Style, init

# Initialize colorama
init()

# Configuration
API_URL = "https://api.findameetingspot.com"
TEST_ENDPOINTS = ["/debug/db-check", "/debug/health", "/api/v1/test/"]
TEST_ORIGINS = ["https://findameetingspot.com"]


def print_colored(message, color):
    """Print a colored message."""
    print(f"{color}{message}{Style.RESET_ALL}")


def test_endpoint(endpoint, origin):
    """Test CORS headers for an endpoint with a specific origin."""
    url = f"{API_URL}{endpoint}"

    print_colored(f"\nTesting {url} with Origin: {origin}", Fore.BLUE)

    # Test OPTIONS (preflight) request
    headers = {
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Content-Type,Authorization",
    }

    try:
        # Preflight request
        print_colored("OPTIONS request (preflight):", Fore.BLUE)
        options_response = requests.options(url, headers=headers, timeout=10)
        print(f"Status: {options_response.status_code}")

        for header, value in options_response.headers.items():
            if header.startswith("Access-Control"):
                print_colored(f"  {header}: {value}", Fore.GREEN)

        if "Access-Control-Allow-Origin" not in options_response.headers:
            print_colored("  Missing Access-Control-Allow-Origin header!", Fore.RED)

        # Actual request
        print_colored("\nGET request:", Fore.BLUE)
        headers = {"Origin": origin}
        get_response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {get_response.status_code}")

        for header, value in get_response.headers.items():
            if header.startswith("Access-Control"):
                print_colored(f"  {header}: {value}", Fore.GREEN)

        if "Access-Control-Allow-Origin" not in get_response.headers:
            print_colored("  Missing Access-Control-Allow-Origin header!", Fore.RED)

    except Exception as e:
        print_colored(f"Error: {str(e)}", Fore.RED)


def main():
    """Run CORS tests for all endpoints and origins."""
    print_colored("=== CORS Test for Deployed API ===", Fore.BLUE)

    for origin in TEST_ORIGINS:
        for endpoint in TEST_ENDPOINTS:
            test_endpoint(endpoint, origin)

    print_colored("\n=== Test Complete ===", Fore.BLUE)


if __name__ == "__main__":
    main()
