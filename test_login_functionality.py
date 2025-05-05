#!/usr/bin/env python3
"""
Test login functionality and database connection.

This script checks database connectivity and verifies that the User model
can be properly accessed and used for authentication.
"""

import sys
import logging
from flask import Flask
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash, check_password_hash

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("login_test")

def test_database_connection():
    """Test database connection and User model functionality."""
    logger.info("Testing database connection and User model...")
    
    try:
        from app import create_app, db
        from app.models.user import User
        
        # Create test application context
        app = create_app("development")
        
        with app.app_context():
            # Test database connection
            logger.info("Testing database connection...")
            try:
                db.engine.connect()
                logger.info("✅ Database connection successful")
            except SQLAlchemyError as e:
                logger.error(f"❌ Database connection failed: {str(e)}")
                return False
            
            # Test User model query
            logger.info("Testing User model query...")
            try:
                user_count = User.query.count()
                logger.info(f"✅ Found {user_count} users in database")
            except SQLAlchemyError as e:
                logger.error(f"❌ Error querying User model: {str(e)}")
                return False
            
            # Test login with first user
            logger.info("Testing user authentication...")
            try:
                test_user = User.query.first()
                if not test_user:
                    logger.warning("⚠️ No users found in database to test login")
                    return True
                
                logger.info(f"Testing user: {test_user.email}")
                
                # Test to_dict method
                try:
                    user_dict = test_user.to_dict()
                    logger.info(f"✅ User.to_dict() works: {user_dict.get('email')}")
                except Exception as e:
                    logger.error(f"❌ Error calling to_dict(): {str(e)}")
                    return False
                
                # Test token generation
                try:
                    token = test_user.generate_access_token()
                    logger.info(f"✅ Token generation works: {token[:15]}...")
                except Exception as e:
                    logger.error(f"❌ Error generating token: {str(e)}")
                    return False
                
                return True
                
            except Exception as e:
                logger.error(f"❌ Error during login test: {str(e)}")
                return False
            
    except ImportError as e:
        logger.error(f"❌ Import error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    if test_database_connection():
        logger.info("✅ All tests passed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Tests failed")
        sys.exit(1) 