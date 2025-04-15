"""Create meeting_contacts association table

Revision ID: c3a410f5e9d2
Revises: b2a430f4e9c1
Create Date: 2025-04-15 14:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c3a410f5e9d2"
down_revision = "b2a430f4e9c1"  # Use the latest migration ID
branch_labels = None
depends_on = None


def upgrade():
    # Create meeting_contacts association table
    op.create_table(
        "meeting_contacts",
        sa.Column("meeting_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["meeting_request_id"], ["meeting_requests.request_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("meeting_request_id", "contact_id"),
    )

    # Add indexes for performance
    op.create_index(op.f("ix_meeting_contacts_contact_id"), "meeting_contacts", ["contact_id"], unique=False)
    op.create_index(
        op.f("ix_meeting_contacts_meeting_request_id"), "meeting_contacts", ["meeting_request_id"], unique=False
    )


def downgrade():
    # Drop meeting_contacts association table
    op.drop_index(op.f("ix_meeting_contacts_meeting_request_id"), table_name="meeting_contacts")
    op.drop_index(op.f("ix_meeting_contacts_contact_id"), table_name="meeting_contacts")
    op.drop_table("meeting_contacts")
