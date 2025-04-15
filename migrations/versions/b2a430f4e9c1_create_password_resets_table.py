"""Create password_resets table

Revision ID: b2a430f4e9c1
Revises: 85486b734ee3
Create Date: 2025-04-15 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b2a430f4e9c1"
down_revision = "85486b734ee3"  # The latest migration ID from the migrations/versions folder
branch_labels = None
depends_on = None


def upgrade():
    # Create password_resets table
    op.create_table(
        "password_resets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=True, default=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_password_resets_token"), "password_resets", ["token"], unique=True)


def downgrade():
    # Drop password_resets table
    op.drop_index(op.f("ix_password_resets_token"), table_name="password_resets")
    op.drop_table("password_resets")
