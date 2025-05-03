#!/usr/bin/env python3
"""Debug script for authentication issues in the Find A Meeting Spot API.

This script helps to troubleshoot 500 errors in the login endpoint by:
1. Testing the login endpoint with various inputs
2. Checking JWT configuration
3. Verifying the user model's password hashing and token generation
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta

import jwt
import requests
from dotenv import load_dotenv
from flask import Flask
from werkzeug.security import check_password_hash, generate_password_hash

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s", handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("auth_debug")

# Load environment variables
load_dotenv()


def test_login_request(api_url, email, password):
    """Test a login request to the API."""
    logger.info(f"Testing login for {email} at {api_url}")

    try:
        headers = {"Content-Type": "application/json", "User-Agent": "AuthDebugScript/1.0"}

        payload = json.dumps({"email": email, "password": password})

        response = requests.post(f"{api_url}/api/v1/auth/login", headers=headers, data=payload, timeout=10)

        logger.info(f"Status code: {response.status_code}")
        logger.info(f"Response headers: {response.headers}")

        try:
            json_response = response.json()
            logger.info(f"Response body: {json.dumps(json_response, indent=2)}")
        except json.JSONDecodeError:
            logger.error("Response is not valid JSON")
            logger.info(f"Raw response: {response.text}")

        return response

    except requests.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        return None


def test_jwt_token_generation(secret_key=None):
    """Test JWT token generation with the configured secret key."""
    if not secret_key:
        secret_key = os.getenv("JWT_SECRET_KEY", "dev")

    logger.info("Testing JWT token generation")
    logger.info(f"Using JWT_SECRET_KEY (masked): {'*' * min(len(secret_key), 5)}")

    try:
        # Create a test payload
        payload = {"sub": "test-user-id", "exp": datetime.utcnow() + timedelta(hours=1), "email": "test@example.com"}

        # Generate a token
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        logger.info(f"Successfully generated JWT token: {token[:10]}...")

        # Try to decode the token
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        logger.info(f"Successfully decoded JWT token: {decoded}")

        return True

    except Exception as e:
        logger.error(f"JWT token generation error: {str(e)}")
        return False


def test_password_hashing():
    """Test password hashing and verification."""
    logger.info("Testing password hashing functionality")

    test_password = "TestPassword123!"

    try:
        # Generate password hash
        password_hash = generate_password_hash(test_password)
        logger.info(f"Successfully generated password hash: {password_hash[:10]}...")

        # Verify password
        is_valid = check_password_hash(password_hash, test_password)
        logger.info(f"Password verification result: {is_valid}")

        # Test with wrong password
        is_invalid = check_password_hash(password_hash, "WrongPassword")
        logger.info(f"Wrong password verification result (should be False): {is_invalid}")

        return is_valid and not is_invalid

    except Exception as e:
        logger.error(f"Password hashing error: {str(e)}")
        return False


def check_environment_variables():
    """Check that required environment variables are set."""
    logger.info("Checking environment variables...")

    # List of variables to check
    variables = ["JWT_SECRET_KEY", "ENCRYPTION_KEY", "SECRET_KEY"]

    all_set = True
    for var in variables:
        value = os.getenv(var)
        if value:
            logger.info(f"{var} is set (masked): {'*' * min(len(value), 5)}")
        else:
            logger.warning(f"{var} is NOT set")
            all_set = False

    return all_set


def main():
    parser = argparse.ArgumentParser(description="Debug authentication issues")
    parser.add_argument("--url", default="https://api.findameetingspot.com", help="API URL")
    parser.add_argument("--email", default="test@example.com", help="Email to test")
    parser.add_argument("--password", default="password", help="Password to test")

    args = parser.parse_args()

    logger.info("=== Find A Meeting Spot Authentication Debugger ===")

    # Run tests
    env_check = check_environment_variables()
    jwt_check = test_jwt_token_generation()
    password_check = test_password_hashing()

    if not env_check:
        logger.warning("Some environment variables are missing or empty")

    if not jwt_check:
        logger.error("JWT token generation test failed")

    if not password_check:
        logger.error("Password hashing test failed")

    # Test actual login
    login_response = test_login_request(args.url, args.email, args.password)

    # Summary
    logger.info("\n=== Debug Summary ===")
    logger.info(f"Environment variables check: {'PASSED' if env_check else 'FAILED'}")
    logger.info(f"JWT token generation check: {'PASSED' if jwt_check else 'FAILED'}")
    logger.info(f"Password hashing check: {'PASSED' if password_check else 'FAILED'}")
    if login_response:
        logger.info(f"Login API test: {'PASSED' if login_response.status_code == 200 else 'FAILED'}")
    else:
        logger.info("Login API test: FAILED (request error)")

    # Recommendations based on results
    logger.info("\n=== Recommendations ===")
    if not env_check:
        logger.info("- Ensure all required environment variables are set in the production environment")
    if not jwt_check:
        logger.info("- Check JWT_SECRET_KEY configuration and make sure it's correctly deployed")
    if not password_check:
        logger.info("- Investigate password hashing implementation in your codebase")
    if login_response and login_response.status_code == 500:
        logger.info("- Check server logs for detailed error messages when 500 error occurs")
        logger.info("- Consider enabling more verbose error logging for the authentication endpoints")


if __name__ == "__main__":
    main()
