"""Add profile_picture_url field to users table

Revision ID: add_profile_picture_url_field
Revises: add_phone_field_to_users
Create Date: 2025-05-03 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "add_profile_picture_url_field"
down_revision = "add_phone_field_to_users"  # Updated to match the previous migration
branch_labels = None
depends_on = None


def upgrade():
    # Check if column exists before adding it
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("users")]

    if "profile_picture_url" not in columns:
        # Add profile_picture_url column to users table
        op.add_column("users", sa.Column("profile_picture_url", sa.String(length=255), nullable=True))


def downgrade():
    # Check if column exists before dropping it
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("users")]

    if "profile_picture_url" in columns:
        # Remove column during downgrade
        op.drop_column("users", "profile_picture_url")
