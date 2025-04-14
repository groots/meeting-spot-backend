#!/bin/bash

# Script to test CORS configuration before deployment

# Set default values
PORT=8081
API_URL="https://api.findameetingspot.com"
MODE="local"  # Options: local, deployed, both

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port=*)
      PORT="${1#*=}"
      shift
      ;;
    --api-url=*)
      API_URL="${1#*=}"
      shift
      ;;
    --mode=*)
      MODE="${1#*=}"
      shift
      ;;
    --help)
      echo "Usage: $0 [--port=PORT] [--api-url=API_URL] [--mode=MODE]"
      echo "  --port=PORT        Port for local testing (default: 8081)"
      echo "  --api-url=API_URL  URL for deployed API testing (default: https://api.findameetingspot.com)"
      echo "  --mode=MODE        Test mode: local, deployed, or both (default: local)"
      echo "  --help             Display this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Check for required dependencies
check_dependency() {
  if ! command -v "$1" &> /dev/null; then
    echo "Error: $1 is required but not installed. Please install it first."
    exit 1
  fi
}

check_dependency python3
check_dependency pip
check_dependency virtualenv

# Set up Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
  echo "Setting up virtual environment..."
  virtualenv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install required packages
echo "Installing required packages..."
pip install -q requests colorama pytest

# Check if Flask is installed, if not install it
if ! python -c "import flask" &> /dev/null; then
  echo "Installing Flask and dependencies..."
  pip install -r requirements.txt
fi

# Run tests based on mode
if [[ "$MODE" == "local" || "$MODE" == "both" ]]; then
  echo "============================================="
  echo "Running CORS tests on local development server"
  echo "============================================="
  python test_cors_predeployment.py --port=$PORT
  LOCAL_STATUS=$?
fi

if [[ "$MODE" == "deployed" || "$MODE" == "both" ]]; then
  echo "============================================="
  echo "Running CORS tests on deployed API: $API_URL"
  echo "============================================="
  python test_cors_deployed.py --api-url=$API_URL
  DEPLOYED_STATUS=$?
fi

# Deactivate virtual environment
deactivate

# Summarize results
echo ""
echo "============================================="
echo "                TEST SUMMARY                 "
echo "============================================="

if [[ "$MODE" == "local" || "$MODE" == "both" ]]; then
  if [ $LOCAL_STATUS -eq 0 ]; then
    echo "Local tests: ✅ PASSED"
  else
    echo "Local tests: ❌ FAILED"
  fi
fi

if [[ "$MODE" == "deployed" || "$MODE" == "both" ]]; then
  if [ $DEPLOYED_STATUS -eq 0 ]; then
    echo "Deployed tests: ✅ PASSED"
  else
    echo "Deployed tests: ❌ FAILED"
  fi
fi

echo "============================================="

# Return overall status
if [[ "$MODE" == "both" ]]; then
  if [ $LOCAL_STATUS -eq 0 ] && [ $DEPLOYED_STATUS -eq 0 ]; then
    echo "All tests passed! Your API is CORS-compliant. ✅"
    exit 0
  else
    echo "Some tests failed. Please check the output above. ❌"
    exit 1
  fi
elif [[ "$MODE" == "local" ]]; then
  if [ $LOCAL_STATUS -eq 0 ]; then
    echo "Local tests passed! Your local API is CORS-compliant. ✅"
    exit 0
  else
    echo "Local tests failed. Please check the output above. ❌"
    exit 1
  fi
elif [[ "$MODE" == "deployed" ]]; then
  if [ $DEPLOYED_STATUS -eq 0 ]; then
    echo "Deployed tests passed! Your deployed API is CORS-compliant. ✅"
    exit 0
  else
    echo "Deployed tests failed. Please check the output above. ❌"
    exit 1
  fi
fi
