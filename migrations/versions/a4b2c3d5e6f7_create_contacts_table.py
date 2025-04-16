"""Create contacts table

Revision ID: a4b2c3d5e6f7
Revises: 84151472c340
Create Date: 2025-04-16 14:20:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "a4b2c3d5e6f7"
down_revision = "84151472c340"  # This should be the latest migration
branch_labels = None
depends_on = None


def upgrade():
    # Create contacts table
    op.create_table(
        "contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add indexes for performance
    op.create_index(op.f("ix_contacts_user_id"), "contacts", ["user_id"], unique=False)
    op.create_index(op.f("ix_contacts_email"), "contacts", ["email"], unique=False)


def downgrade():
    # Drop contacts table
    op.drop_index(op.f("ix_contacts_email"), table_name="contacts")
    op.drop_index(op.f("ix_contacts_user_id"), table_name="contacts")
    op.drop_table("contacts")
