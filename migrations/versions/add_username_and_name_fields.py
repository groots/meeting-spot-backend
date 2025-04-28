"""Add username and name fields to users table

Revision ID: abc123def456
Revises: 1de9095caa6e
Create Date: 2025-04-28 14:30:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "abc123def456"
down_revision = "1de9095caa6e"  # Update this to match your latest migration
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to the users table
    op.add_column("users", sa.Column("username", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("first_name", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(length=50), nullable=True))

    # Create an index on the username column for faster lookups
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    # Generate usernames from email addresses for existing users
    op.execute(
        """
    UPDATE users
    SET username = SUBSTRING(email FROM 1 FOR POSITION('@' IN email) - 1)
    WHERE username IS NULL
    """
    )


def downgrade():
    # Drop the index first
    op.drop_index(op.f("ix_users_username"), table_name="users")

    # Then drop the columns
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
    op.drop_column("users", "username")
