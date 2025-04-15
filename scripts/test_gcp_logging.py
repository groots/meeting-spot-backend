#!/usr/bin/env python
"""
Script to test Google Cloud Logging access
"""
import logging
import os
import sys
from datetime import datetime

# Add parent directory to path to allow importing app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    # Try importing the Google Cloud Logging client
    from google.cloud import logging as gcp_logging

    print("✅ Successfully imported Google Cloud Logging")

    # Test creating a client
    try:
        client = gcp_logging.Client()
        print(f"✅ Successfully created logging client")

        # Try to get some logs
        print("Fetching recent logs...")
        entries = client.list_entries(page_size=5, order_by="timestamp desc")

        count = 0
        for entry in entries:
            count += 1
            print(f"\nLog Entry {count}:")
            print(f"  Timestamp: {entry.timestamp}")
            print(f"  Severity: {entry.severity}")

            # Try to get the payload
            if hasattr(entry, "payload") and entry.payload:
                print(f"  Payload: {type(entry.payload)}")
                if isinstance(entry.payload, dict):
                    for k, v in entry.payload.items():
                        print(f"    {k}: {v}")
                else:
                    print(f"    {entry.payload}")
            elif hasattr(entry, "text_payload") and entry.text_payload:
                print(f"  Text Payload: {entry.text_payload[:100]}...")
            elif hasattr(entry, "json_payload") and entry.json_payload:
                print(f"  JSON Payload: {dict(entry.json_payload)}")

            if count >= 5:
                break

        if count == 0:
            print("No logs found. Check permissions or try a different project.")

    except Exception as e:
        print(f"❌ Error creating logging client: {e}")

except ImportError as e:
    print(f"❌ Failed to import Google Cloud Logging: {e}")
    print("Run 'pip install google-cloud-logging' to install the required package")

print("\nEnvironment Information:")
print(f"GOOGLE_CLOUD_PROJECT: {os.environ.get('GOOGLE_CLOUD_PROJECT', 'Not set')}")
print(f"GOOGLE_APPLICATION_CREDENTIALS: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'Not set')}")
