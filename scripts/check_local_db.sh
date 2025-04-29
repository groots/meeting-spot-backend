#!/bin/bash

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Checking local database schema...${NC}"

# Change to the backend directory if script is called from elsewhere
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "${SCRIPT_DIR}/.." || exit 1

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is required but not installed.${NC}"
    exit 1
fi

# Check if required Python modules are installed
echo -e "${YELLOW}Checking Python dependencies...${NC}"
python3 -c "import sqlalchemy" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}SQLAlchemy not found. Installing requirements...${NC}"
    pip install -r requirements.txt
fi

# Run the verification script
echo -e "${YELLOW}Running database schema verification...${NC}"
python3 -c "
import sys
sys.path.append('.')
from verify_db_schema import main, check_user_data, get_db_url, verify_columns
from sqlalchemy import create_engine

try:
    # Get database URL
    db_url = get_db_url()
    masked_url = db_url.replace(db_url.split(':')[2].split('@')[0], '***')
    print(f'Using database URL: {masked_url}')

    # Create engine
    engine = create_engine(db_url)

    # Verify columns
    columns_exist = verify_columns(engine)
    print(f'Column verification: {\"PASSED\" if columns_exist else \"FAILED\"}')

    # Check user data
    if columns_exist:
        users_with_username, users_without_username = check_user_data(engine)
        print(f'Users with username: {users_with_username}')
        print(f'Users without username: {users_without_username}')

        if users_without_username > 0:
            print(f'\\n{users_without_username} users still need usernames')
        else:
            print('\\nAll users have usernames!')

    # Exit with appropriate code
    if columns_exist and users_without_username == 0:
        print('\\n✓ Database schema looks good!')
        sys.exit(0)
    else:
        print('\\n⚠ Database schema needs attention. Please review the results above.')
        sys.exit(1)

except Exception as e:
    print(f'Error checking database: {str(e)}')
    sys.exit(1)
"

# Capture the exit code
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}Database verification completed successfully.${NC}"
else
    echo -e "${RED}Database verification failed. Check the output above for details.${NC}"
fi

exit $EXIT_CODE
