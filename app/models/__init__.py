"""Models package."""

from sqlalchemy import inspect

# Import the db instance for other modules that import it from here
from .. import db

# Import model classes - fix imports to use the correct modules
from .user import User
from .enums import ContactType, MeetingRequestStatus
from .meeting_request import MeetingRequest
from .contact import Contact

# Import other models that might exist in different environments
try:
    from .place import Place
except ImportError:
    # Place model might not exist in all environments
    Place = None

try:
    from .subscription import Subscription
except ImportError:
    # Subscription model might not exist in all environments
    Subscription = None


# This function will be called by the app factory to initialize model schemas
def init_models(app, db):
    """Initialize models based on database schema."""
    with app.app_context():
        # Skip if tables don't exist yet (e.g., during migrations)
        inspector = inspect(db.engine)
        if not inspector.has_table("users"):
            app.logger.info("Users table doesn't exist yet, skipping model initialization")
            return

        # Initialize User model
        if hasattr(User, "__declare_last__"):
            try:
                # Call __declare_last__ manually
                User.__declare_last__()
                app.logger.info("User model initialized successfully")
            except Exception as e:
                app.logger.error(f"Error initializing User model: {str(e)}")

        # Initialize Subscription model if it exists
        if Subscription and hasattr(Subscription, "__declare_last__"):
            try:
                # Call __declare_last__ manually
                Subscription.__declare_last__()
                app.logger.info("Subscription model initialized successfully")
            except Exception as e:
                app.logger.error(f"Error initializing Subscription model: {str(e)}")

        # Initialize Place model if it exists
        if Place and hasattr(Place, "__declare_last__"):
            try:
                # Call __declare_last__ manually
                Place.__declare_last__()
                app.logger.info("Place model initialized successfully")
            except Exception as e:
                app.logger.error(f"Error initializing Place model: {str(e)}")

        # Initialize other models as needed
