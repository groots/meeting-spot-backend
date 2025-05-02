#!/bin/bash

# Test script for verifying the fixes for middleware and profile picture upload

# Color codes for better readability
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}===================================================${NC}"
echo -e "${GREEN}  Running tests for middleware and profile picture fixes${NC}"
echo -e "${GREEN}===================================================${NC}"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo -e "${GREEN}Activated virtual environment${NC}"
elif [ -d "../venv" ]; then
    source ../venv/bin/activate
    echo -e "${GREEN}Activated virtual environment from parent directory${NC}"
else
    echo -e "${YELLOW}No virtual environment found, using system Python${NC}"
fi

# Set environment to testing
export FLASK_ENV=testing
export FLASK_APP=app
export DATABASE_URL="sqlite:///:memory:"

# Apply the fixes first to ensure they're in place
echo -e "${GREEN}Applying fixes before testing...${NC}"
if [ -f "deploy_middleware_fix.sh" ]; then
    bash deploy_middleware_fix.sh
elif [ -f "../deploy_middleware_fix.sh" ]; then
    bash ../deploy_middleware_fix.sh
else
    echo -e "${YELLOW}deploy_middleware_fix.sh not found, skipping pre-test fixes${NC}"
fi

# Create instance directory for profile pictures if it doesn't exist
mkdir -p instance/profile_pictures
chmod 755 instance/profile_pictures

# Run the dedicated test file for fixes
echo -e "${GREEN}Running fix-specific tests...${NC}"
if python -m pytest tests/test_fixes.py -v; then
    echo -e "${GREEN}✅ Fix-specific tests passed!${NC}"
    all_tests_passed=true
else
    echo -e "${RED}❌ Fix-specific tests failed!${NC}"
    all_tests_passed=false
fi

# Run the full test suite to ensure no regressions
echo -e "${GREEN}Running full test suite to check for regressions...${NC}"
if python -m pytest; then
    echo -e "${GREEN}✅ Full test suite passed!${NC}"
    full_suite_passed=true
else
    echo -e "${RED}❌ Some tests in the full suite failed!${NC}"
    full_suite_passed=false
fi

echo ""
echo -e "${GREEN}===================================================${NC}"
if $all_tests_passed && $full_suite_passed; then
    echo -e "${GREEN}✅ All tests passed successfully!${NC}"
    echo -e "${GREEN}The fixes for middleware and profile picture upload${NC}"
    echo -e "${GREEN}have been successfully applied and verified.${NC}"

    # Add git commit if fixes passed
    if command -v git >/dev/null 2>&1; then
        echo -e "${GREEN}Committing the fixes to git...${NC}"
        git add app/middleware.py app/__init__.py \
               tests/test_fixes.py \
               deploy_middleware_fix.sh \
               test_fixes.sh \
               README-FIXES.md \
               migrations/versions/add_profile_picture_url_field.py
        git commit -m "Fix middleware registration and profile picture upload issues"

        # Push if remote exists
        if git remote -v | grep -q origin; then
            echo -e "${GREEN}Pushing the fixes to the remote repository...${NC}"
            git push origin HEAD
        else
            echo -e "${YELLOW}No remote repository found, skipping push${NC}"
        fi
    else
        echo -e "${YELLOW}Git not available, skipping commit${NC}"
    fi

    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please check the output above.${NC}"
    echo -e "${RED}The fixes may not be completely applied or verified.${NC}"
    exit 1
fi
