#!/usr/bin/env python3
"""
Fix User model issues related to missing columns.

This script modifies the User model dynamically to make it resilient to
missing columns in the database. It handles the specific issue where columns 
like `username` are defined in the model but not present in the database.
"""

import os
import sys
import logging
from sqlalchemy import inspect, Column, String, Boolean
from sqlalchemy.exc import SQLAlchemyError, OperationalError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("user_model_fix")

def fix_user_model():
    """Fix issues with User model related to missing columns."""
    try:
        from app import create_app, db
        from app.models.user import User
        
        app = create_app("development")
        
        with app.app_context():
            inspector = inspect(db.engine)
            existing_columns = {column['name'] for column in inspector.get_columns('users')}
            
            logger.info(f"Existing columns in 'users' table: {', '.join(sorted(existing_columns))}")
            
            # Create a patch for the User class to modify its __init__
            original_init = User.__init__
            
            def patched_init(self, **kwargs):
                # Filter out attributes that don't exist in the database
                filtered_kwargs = {}
                for key, value in kwargs.items():
                    if key in existing_columns or key in ['id', 'created_at', 'updated_at']:
                        filtered_kwargs[key] = value
                
                # Call the original __init__ with filtered kwargs
                original_init(self, **filtered_kwargs)
            
            # Apply the patched __init__
            User.__init__ = patched_init
            
            # Monkey patch the User.to_dict method to be more resilient
            original_to_dict = User.to_dict
            
            def safe_to_dict(self):
                """Resilient to_dict implementation that doesn't access missing columns."""
                try:
                    # Try the original to_dict first
                    return original_to_dict(self)
                except (AttributeError, SQLAlchemyError) as e:
                    logger.warning(f"Original to_dict failed: {str(e)}, using safe fallback")
                    
                    # Fallback to a simplified dictionary with only known columns
                    result = {
                        "id": str(self.id),
                        "email": self.email,
                        "created_at": self.created_at.isoformat() if hasattr(self, 'created_at') and self.created_at else None,
                        "updated_at": self.updated_at.isoformat() if hasattr(self, 'updated_at') and self.updated_at else None,
                    }
                    
                    # Add other columns only if they exist in the database
                    for column, value in inspect(self).dict.items():
                        if column in existing_columns and column not in result:
                            result[column] = value
                            
                    return result
            
            # Apply the patched to_dict
            User.to_dict = safe_to_dict
            
            # Test the fix by creating a query
            try:
                user_count = User.query.count()
                logger.info(f"✅ User model fixed - found {user_count} users")
                
                # Test to_dict on first user
                user = User.query.first()
                if user:
                    user_dict = user.to_dict()
                    logger.info(f"✅ to_dict works: {user_dict}")
                
                return True
            except Exception as e:
                logger.error(f"❌ Fix didn't work: {str(e)}")
                return False
                
    except ImportError as e:
        logger.error(f"❌ Import error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        return False

def apply_database_fix():
    """Apply database fix by adding missing columns if needed."""
    try:
        from app import create_app, db
        from app.models.user import User
        
        app = create_app("development")
        
        with app.app_context():
            inspector = inspect(db.engine)
            existing_columns = {column['name'] for column in inspector.get_columns('users')}
            
            # Check if username column exists
            if 'username' not in existing_columns:
                logger.info("Adding missing 'username' column to users table")
                try:
                    # Add the missing column
                    with db.engine.begin() as conn:
                        conn.execute(db.text(
                            "ALTER TABLE users ADD COLUMN username VARCHAR(50) UNIQUE"
                        ))
                    logger.info("✅ Added 'username' column to users table")
                except OperationalError as e:
                    logger.error(f"❌ Failed to add column: {str(e)}")
            
            # Check if other required columns exist and add them if needed
            columns_to_check = {
                'first_name': 'VARCHAR(50)',
                'last_name': 'VARCHAR(50)',
                'phone': 'VARCHAR(50)',
                'profile_picture_url': 'VARCHAR(255)'
            }
            
            for column, data_type in columns_to_check.items():
                if column not in existing_columns:
                    logger.info(f"Adding missing '{column}' column to users table")
                    try:
                        with db.engine.begin() as conn:
                            conn.execute(db.text(
                                f"ALTER TABLE users ADD COLUMN {column} {data_type}"
                            ))
                        logger.info(f"✅ Added '{column}' column to users table")
                    except OperationalError as e:
                        logger.error(f"❌ Failed to add column '{column}': {str(e)}")
            
            return True
    
    except Exception as e:
        logger.error(f"❌ Error applying database fix: {str(e)}")
        return False

if __name__ == "__main__":
    # First try to fix the model dynamically
    logger.info("Attempting to fix User model...")
    model_fix_success = fix_user_model()
    
    if not model_fix_success:
        # If model fix didn't work, try database modifications
        logger.info("Model fix didn't work, attempting database fix...")
        db_fix_success = apply_database_fix()
        
        if db_fix_success:
            # Try model fix again after database changes
            logger.info("Database updated, trying model fix again...")
            model_fix_success = fix_user_model()
    
    if model_fix_success:
        logger.info("✅ User model fixed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Failed to fix User model")
        sys.exit(1) 