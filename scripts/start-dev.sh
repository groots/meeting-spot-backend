#!/bin/bash

# Start Cloud SQL Proxy in the background
cloud-sql-proxy --port 5433 find-a-meeting-spot:us-east1:findameetingspot &
PROXY_PID=$!

# Wait for the proxy to start
sleep 2

# Start Flask development server
python development.py

# Kill the Cloud SQL proxy when the Flask server exits
kill $PROXY_PID
