"""Add facebook_oauth_id to users table

This migration adds a facebook_oauth_id column to the users table to enable Facebook authentication.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision = "add_facebook_oauth"
down_revision = None
depends_on = None


def upgrade():
    """Add facebook_oauth_id column to users table."""
    try:
        # Check if the column already exists
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        columns = [col["name"] for col in inspector.get_columns("users")]

        if "facebook_oauth_id" not in columns:
            op.add_column("users", sa.Column("facebook_oauth_id", sa.String(255), nullable=True, unique=True))

            # Add index for faster lookups
            op.create_index("ix_users_facebook_oauth_id", "users", ["facebook_oauth_id"], unique=True)

            print("Successfully added facebook_oauth_id column to users table")
        else:
            print("facebook_oauth_id column already exists in users table")
    except Exception as e:
        print(f"Error adding facebook_oauth_id column: {str(e)}")
        raise


def downgrade():
    """Remove facebook_oauth_id column from users table."""
    try:
        op.drop_index("ix_users_facebook_oauth_id", table_name="users")
        op.drop_column("users", "facebook_oauth_id")
        print("Successfully removed facebook_oauth_id column from users table")
    except Exception as e:
        print(f"Error removing facebook_oauth_id column: {str(e)}")
        raise
