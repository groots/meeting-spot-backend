#!/bin/bash

# Get authentication token from gcloud
TOKEN=$(gcloud auth print-identity-token)

# Call the verification service
echo "Checking database schema..."
curl -H "Authorization: Bearer $TOKEN" https://db-schema-verifier-vn5dwnwlzq-ue.a.run.app/
