"""Add password_resets table

Revision ID: 9a8e4f2b5c1d
Revises: (use the latest revision ID in your migrations folder)
Create Date: 2025-04-14 21:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "9a8e4f2b5c1d"
down_revision = None  # Replace with the latest revision ID when running
branch_labels = None
depends_on = None


def upgrade():
    # Create password_resets table
    op.create_table(
        "password_resets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token", sa.String(length=100), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, default=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_password_resets_token"), "password_resets", ["token"], unique=True)


def downgrade():
    # Drop password_resets table
    op.drop_index(op.f("ix_password_resets_token"), table_name="password_resets")
    op.drop_table("password_resets")
