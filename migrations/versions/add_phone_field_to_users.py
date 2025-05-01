"""Add phone field to users table

Revision ID: add_phone_field_to_users
Revises: 5d23d885851c
Create Date: 2025-05-01 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_phone_field_to_users"
down_revision = "5d23d885851c"  # Updated to match the latest migration
branch_labels = None
depends_on = None


def upgrade():
    # Add phone column to users table
    op.add_column("users", sa.Column("phone", sa.String(length=50), nullable=True))

    # Create an index on the phone column for faster lookups
    op.create_index(op.f("ix_users_phone"), "users", ["phone"], unique=False)


def downgrade():
    # Remove index and column during downgrade
    op.drop_index(op.f("ix_users_phone"), table_name="users")
    op.drop_column("users", "phone") 