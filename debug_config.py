#!/usr/bin/env python3

"""
Debug script to check the server configuration and middleware registration.
This script will output information about the Flask app configuration,
particularly related to the ENCRYPTION_KEY.
"""

import os
import sys
from pprint import pprint

# Add the current directory to the path to import from app
sys.path.insert(0, os.path.abspath("."))
print(f"Current working directory: {os.getcwd()}")

try:
    # Import the create_app function
    from app import create_app

    # Create a test app
    app = create_app("development")

    # Check if middleware is registered
    middleware_registered = (
        hasattr(app, "_before_request_funcs")
        and app._before_request_funcs
        and len(app._before_request_funcs.get(None, [])) > 0
    )

    print("=" * 50)
    print("App Configuration:")
    print("=" * 50)

    # Print the app config
    app_config = {k: v for k, v in app.config.items() if not k.startswith("_")}

    # Special handling for ENCRYPTION_KEY - Don't print the actual key
    if "ENCRYPTION_KEY" in app_config:
        app_config["ENCRYPTION_KEY"] = "[REDACTED]" if app_config["ENCRYPTION_KEY"] else None
    else:
        app_config["ENCRYPTION_KEY"] = "MISSING!"

    pprint(app_config)

    print("\n" + "=" * 50)
    print("Middleware Status:")
    print("=" * 50)
    print(f"Middleware functions registered: {middleware_registered}")

    if middleware_registered:
        print(f"Number of middleware functions: {len(app._before_request_funcs.get(None, []))}")
        for i, func in enumerate(app._before_request_funcs.get(None, [])):
            print(f"  {i+1}. {func.__module__}.{func.__name__}")

    # Check if register_middleware function exists in the middleware module
    try:
        from app.middleware import register_middleware

        print("\nregister_middleware function exists in app.middleware")
    except ImportError:
        print("\nregister_middleware function DOES NOT exist in app.middleware")

    # Check if ENCRYPTION_KEY is being properly set
    if app.config.get("ENCRYPTION_KEY"):
        print("\nENCRYPTION_KEY is set in the app config")
    else:
        print("\nENCRYPTION_KEY is NOT set in the app config")

except Exception as e:
    print(f"Error: {str(e)}")
    import traceback

    traceback.print_exc()
