"""Fix missing username fields in users table

Revision ID: fix_missing_username
Revises: add_facebook_oauth
Create Date: 2025-04-29 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "fix_missing_username"
down_revision = "add_facebook_oauth"  # Make sure this matches your latest migration
branch_labels = None
depends_on = None


def upgrade():
    """Add username and name fields to users table if they don't exist."""
    try:
        # Check if columns already exist
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        columns = [col["name"] for col in inspector.get_columns("users")]

        # Add username column if it doesn't exist
        if "username" not in columns:
            op.add_column("users", sa.Column("username", sa.String(length=50), nullable=True))
            op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
            print("Added username column to users table")

        # Add first_name column if it doesn't exist
        if "first_name" not in columns:
            op.add_column("users", sa.Column("first_name", sa.String(length=50), nullable=True))
            print("Added first_name column to users table")

        # Add last_name column if it doesn't exist
        if "last_name" not in columns:
            op.add_column("users", sa.Column("last_name", sa.String(length=50), nullable=True))
            print("Added last_name column to users table")

        # Add facebook_oauth_id column if it doesn't exist
        if "facebook_oauth_id" not in columns:
            op.add_column("users", sa.Column("facebook_oauth_id", sa.String(255), nullable=True))
            op.create_index(op.f("ix_users_facebook_oauth_id"), "users", ["facebook_oauth_id"], unique=True)
            print("Added facebook_oauth_id column to users table")

        # Generate usernames from email addresses for existing users
        op.execute(
            """
        UPDATE users
        SET username = SUBSTRING(email FROM 1 FOR POSITION('@' IN email) - 1)
        WHERE username IS NULL
        """
        )
        print("Generated usernames for existing users")

    except Exception as e:
        print(f"Error adding columns: {str(e)}")
        raise


def downgrade():
    """Remove added columns (if needed)."""
    # Only execute if you need to roll back these changes
    try:
        # We should drop indexes first
        try:
            op.drop_index(op.f("ix_users_username"), table_name="users")
            print("Dropped username index")
        except Exception:
            print("Username index may not exist, continuing...")

        try:
            op.drop_index(op.f("ix_users_facebook_oauth_id"), table_name="users")
            print("Dropped facebook_oauth_id index")
        except Exception:
            print("Facebook OAuth ID index may not exist, continuing...")

        # Then drop columns
        op.drop_column("users", "username")
        op.drop_column("users", "first_name")
        op.drop_column("users", "last_name")
        op.drop_column("users", "facebook_oauth_id")

        print("Successfully removed added columns")
    except Exception as e:
        print(f"Error removing columns: {str(e)}")
        raise
