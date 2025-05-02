#!/bin/bash
# apply_phone_column_hotfix.sh
# Script to fix the missing 'phone' column in the users table in production

set -e  # Exit on error

# Print colored output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting phone column hotfix for meeting requests 500 error${NC}"

# Check if we're in the backend directory
if [ ! -d "app" ]; then
    echo -e "${RED}Error: This script must be run from the backend directory${NC}"
    exit 1
fi

# Create backup directory
echo -e "${YELLOW}Creating backup...${NC}"
BACKUP_DIR="backup_phone_column_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Verify the migration file exists
if [ ! -f "migrations/versions/add_phone_column_hotfix.py" ]; then
    echo -e "${RED}Error: Migration file migrations/versions/add_phone_column_hotfix.py not found${NC}"
    exit 1
fi

# Backup the database if possible (this depends on your setup)
echo -e "${YELLOW}Checking for database backup capability...${NC}"
if [ -x "$(command -v pg_dump)" ] && [ ! -z "$DATABASE_URL" ]; then
    echo -e "${YELLOW}Attempting database backup...${NC}"
    pg_dump "$DATABASE_URL" > "$BACKUP_DIR/db_backup.sql" || echo -e "${YELLOW}Database backup failed, but continuing with migration${NC}"
else
    echo -e "${YELLOW}Database backup tools not available, proceeding without backup${NC}"
fi

# Run the migration
echo -e "${YELLOW}Running database migration to add phone column...${NC}"
export FLASK_APP=wsgi.py
export FLASK_ENV=production

# First check existing columns to verify the issue
echo -e "${YELLOW}Checking existing columns in users table...${NC}"
python3 -c "
from sqlalchemy import inspect, create_engine
import os
from sqlalchemy.engine.url import make_url

# Get database URL from environment or use a default
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print('${RED}No DATABASE_URL found in environment${NC}')
    # Try to get it from config
    try:
        from app import create_app
        app = create_app('production')
        with app.app_context():
            db_url = app.config.get('SQLALCHEMY_DATABASE_URI')
    except Exception as e:
        print(f'${RED}Error getting database URL from app config: {e}${NC}')
        exit(1)

print(f'${YELLOW}Using database URL: {db_url.split(\"@\")[1] if \"@\" in db_url else \"*****\"}${NC}')
engine = create_engine(db_url)
inspector = inspect(engine)

if 'users' in inspector.get_table_names():
    columns = [col['name'] for col in inspector.get_columns('users')]
    print(f'${YELLOW}Existing columns in users table: {columns}${NC}')
    if 'phone' in columns:
        print('${GREEN}phone column already exists!${NC}')
    else:
        print('${RED}phone column is missing!${NC}')
else:
    print('${RED}users table does not exist!${NC}')
"

# Run the migration
echo -e "${YELLOW}Applying migration...${NC}"
flask db upgrade add_phone_column_hotfix

# Verify the migration was successful
echo -e "${YELLOW}Verifying migration...${NC}"
python3 -c "
from sqlalchemy import inspect, create_engine
import os
from sqlalchemy.engine.url import make_url

# Get database URL from environment or use a default
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print('${RED}No DATABASE_URL found in environment${NC}')
    # Try to get it from config
    try:
        from app import create_app
        app = create_app('production')
        with app.app_context():
            db_url = app.config.get('SQLALCHEMY_DATABASE_URI')
    except Exception as e:
        print(f'${RED}Error getting database URL from app config: {e}${NC}')
        exit(1)

engine = create_engine(db_url)
inspector = inspect(engine)

if 'users' in inspector.get_table_names():
    columns = [col['name'] for col in inspector.get_columns('users')]
    if 'phone' in columns:
        print('${GREEN}✅ phone column successfully added to users table!${NC}')
    else:
        print('${RED}❌ Failed to add phone column to users table!${NC}')
        exit(1)
else:
    print('${RED}❌ users table does not exist!${NC}')
    exit(1)
"

# Restart the application server (adjust as needed for your environment)
echo -e "${YELLOW}Restarting application...${NC}"
if [ -f "/etc/systemd/system/findameetingspot.service" ]; then
    echo -e "${YELLOW}Restarting systemd service...${NC}"
    sudo systemctl restart findameetingspot.service
    echo -e "${GREEN}Service restarted${NC}"
elif [ -x "$(command -v docker)" ] && docker ps | grep -q "findameetingspot"; then
    echo -e "${YELLOW}Restarting Docker container...${NC}"
    docker restart $(docker ps | grep findameetingspot | awk '{print $1}')
    echo -e "${GREEN}Docker container restarted${NC}"
elif [ -x "$(command -v supervisorctl)" ]; then
    echo -e "${YELLOW}Restarting supervisor-managed service...${NC}"
    supervisorctl restart findameetingspot
    echo -e "${GREEN}Service restarted${NC}"
else
    echo -e "${YELLOW}No service manager detected. Please restart the application manually.${NC}"
fi

echo -e "${GREEN}Phone column hotfix completed!${NC}"
echo -e "${YELLOW}Please verify that meeting requests and profile picture uploads are now working properly.${NC}"
