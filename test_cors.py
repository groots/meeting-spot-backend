#!/usr/bin/env python3
"""
Test script for CORS configuration in the backend.
This script performs simple CORS tests to help diagnose CORS issues.
"""

import argparse
import json
import logging
import sys

import requests
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(message)s", datefmt="[%X]", handlers=[RichHandler(rich_tracebacks=True)]
)
log = logging.getLogger("cors_test")

console = Console()

# Parse arguments
parser = argparse.ArgumentParser(description="Test CORS configuration.")
parser.add_argument("--url", default="http://localhost:8081", help="Base URL of the API server")
parser.add_argument("--origins", nargs="+", default=["http://localhost:3000"], help="Origins to test")
parser.add_argument(
    "--endpoints",
    nargs="+",
    default=["/debug/cors-check", "/debug/health", "/api/v1/auth/register"],
    help="Endpoints to test",
)
args = parser.parse_args()


def test_cors(base_url, origin, endpoint):
    """Test CORS headers for an endpoint with a specific origin."""
    url = f"{base_url}{endpoint}"

    console.print(f"Testing [blue]{url}[/blue] with Origin: [yellow]{origin}[/yellow]")

    # Test OPTIONS (preflight) request
    headers = {
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Content-Type,Authorization",
    }

    try:
        # Preflight request
        console.print("\nOPTIONS request (preflight):", style="bold")
        options_response = requests.options(url, headers=headers, timeout=10)
        console.print(f"Status: {options_response.status_code}")

        has_cors_header = False
        for header, value in options_response.headers.items():
            if header.startswith("Access-Control"):
                console.print(f"  [green]{header}[/green]: {value}")
                has_cors_header = True

        if not has_cors_header:
            console.print("  [red]No CORS headers found in response![/red]")

        # Actual request
        console.print("\nGET request:", style="bold")
        headers = {"Origin": origin}
        get_response = requests.get(url, headers=headers, timeout=10)
        console.print(f"Status: {get_response.status_code}")

        has_cors_header = False
        for header, value in get_response.headers.items():
            if header.startswith("Access-Control"):
                console.print(f"  [green]{header}[/green]: {value}")
                has_cors_header = True

        if not has_cors_header:
            console.print("  [red]No CORS headers found in response![/red]")

        # Check if /debug/cors-check endpoint and show details
        if endpoint == "/debug/cors-check" and get_response.status_code == 200:
            try:
                data = get_response.json()
                table = Table(title="CORS Check Details")
                table.add_column("Property", style="cyan")
                table.add_column("Value", style="yellow")

                for key, value in data.items():
                    if isinstance(value, list):
                        table.add_row(key, ", ".join(value))
                    else:
                        table.add_row(key, str(value))

                console.print(table)
            except json.JSONDecodeError:
                console.print("[red]Failed to parse JSON response[/red]")

        return has_cors_header
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        return False


def main():
    """Run CORS tests for all endpoints and origins."""
    console.print(Panel("CORS Test for Backend API", style="bold blue"))

    results = []

    for origin in args.origins:
        for endpoint in args.endpoints:
            success = test_cors(args.url, origin, endpoint)
            results.append({"origin": origin, "endpoint": endpoint, "success": success})
            console.print("\n" + "-" * 50 + "\n")

    # Summary
    table = Table(title="CORS Test Summary")
    table.add_column("Origin", style="cyan")
    table.add_column("Endpoint", style="yellow")
    table.add_column("Result", style="green")

    for result in results:
        status = "[green]✓ PASS" if result["success"] else "[red]✗ FAIL"
        table.add_row(result["origin"], result["endpoint"], status)

    console.print(table)

    # Overall result
    if all(result["success"] for result in results):
        console.print("[green]All CORS tests passed![/green]")
    else:
        console.print("[red]Some CORS tests failed.[/red]")
        failed = sum(1 for result in results if not result["success"])
        console.print(f"Failed: {failed} of {len(results)}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
