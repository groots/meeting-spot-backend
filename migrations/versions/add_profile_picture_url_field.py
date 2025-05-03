"""Add profile_picture_url field to users table

Revision ID: add_profile_picture_url_field
Revises:
Create Date: 2023-10-15 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "add_profile_picture_url_field"
down_revision = None  # Set to your previous migration if any
branch_labels = None
depends_on = None


def upgrade():
    """Add profile_picture_url column to users table if it doesn't exist."""
    # Get database connection
    conn = op.get_bind()
    inspector = inspect(conn)

    # Check if the users table exists
    if "users" in inspector.get_table_names():
        # Check if profile_picture_url column already exists to avoid errors
        columns = [col["name"] for col in inspector.get_columns("users")]
        if "profile_picture_url" not in columns:
            # Add profile_picture_url column to users table
            op.add_column("users", sa.Column("profile_picture_url", sa.String(length=255), nullable=True))
            print("Successfully added profile_picture_url column to users table")
        else:
            print("profile_picture_url column already exists in users table")
    else:
        print("users table does not exist in the database")


def downgrade():
    """Remove profile_picture_url column from users table."""
    # Get database connection
    conn = op.get_bind()
    inspector = inspect(conn)

    # Check if the users table exists
    if "users" in inspector.get_table_names():
        # Check if profile_picture_url column exists before attempting to remove it
        columns = [col["name"] for col in inspector.get_columns("users")]
        if "profile_picture_url" in columns:
            op.drop_column("users", "profile_picture_url")
            print("Successfully removed profile_picture_url column from users table")
        else:
            print("profile_picture_url column does not exist in users table")
    else:
        print("users table does not exist in the database")
