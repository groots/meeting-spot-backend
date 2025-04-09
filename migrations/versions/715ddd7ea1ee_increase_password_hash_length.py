"""increase_password_hash_length

Revision ID: 715ddd7ea1ee
Revises: 5c9553c5fdc8
Create Date: 2025-04-09 11:22:07.311047

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "715ddd7ea1ee"
down_revision = "5c9553c5fdc8"
branch_labels = None
depends_on = None


def upgrade():
    # Increase password_hash column length to 256
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(length=128),
        type_=sa.String(length=256),
        existing_nullable=True,
    )


def downgrade():
    # Revert password_hash column length to 128
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(length=256),
        type_=sa.String(length=128),
        existing_nullable=True,
    )
