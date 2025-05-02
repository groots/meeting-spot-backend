"""Add phone column to users table hotfix

Revision ID: add_phone_column_hotfix
Revises: add_profile_picture_url_field
Create Date: 2025-05-03 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "add_phone_column_hotfix"
down_revision = "add_profile_picture_url_field"  # Make sure this matches your latest migration
branch_labels = None
depends_on = None


def upgrade():
    """Add phone column to users table if it doesn't exist."""
    # Get database connection
    conn = op.get_bind()
    inspector = inspect(conn)

    # Check if the users table exists
    if "users" in inspector.get_table_names():
        # Check if phone column already exists to avoid errors
        columns = [col["name"] for col in inspector.get_columns("users")]
        if "phone" not in columns:
            print("Adding phone column to users table")
            op.add_column("users", sa.Column("phone", sa.String(50), nullable=True))
            # Add index for phone column
            op.create_index(op.f("ix_users_phone"), "users", ["phone"], unique=False)
            print("Successfully added phone column to users table")
        else:
            print("phone column already exists in users table")
    else:
        print("users table does not exist in the database")


def downgrade():
    """Remove phone column from users table."""
    # Get database connection
    conn = op.get_bind()
    inspector = inspect(conn)

    # Check if the users table exists
    if "users" in inspector.get_table_names():
        # Check if phone column exists before attempting to remove it
        columns = [col["name"] for col in inspector.get_columns("users")]
        if "phone" in columns:
            print("Removing phone column from users table")
            # Drop the index first
            op.drop_index(op.f("ix_users_phone"), table_name="users")
            # Drop the column
            op.drop_column("users", "phone")
            print("Successfully removed phone column from users table")
        else:
            print("phone column does not exist in users table")
    else:
        print("users table does not exist in the database")
