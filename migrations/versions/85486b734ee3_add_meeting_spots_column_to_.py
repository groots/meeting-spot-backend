"""Add meeting_spots column to MeetingRequest

Revision ID: 85486b734ee3
Revises: 5d23d885851c
Create Date: 2024-03-19 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "85486b734ee3"
down_revision = "5d23d885851c"
branch_labels = None
depends_on = None


def upgrade():
    # Drop the foreign key constraint first
    op.drop_constraint(
        "meeting_requests_user_a_id_fkey",
        "meeting_requests",
        type_="foreignkey")

    # Create a temporary table to store the mapping of old IDs to new UUIDs
    op.create_table(
        "id_mapping",
        sa.Column("old_id", sa.Integer(), nullable=False),
        sa.Column("new_id", sa.UUID(), nullable=False),
    )

    # Insert current user IDs into the mapping table
    op.execute(
        "INSERT INTO id_mapping (old_id, new_id) SELECT id, gen_random_uuid() FROM users")

    # Add a temporary UUID column to users
    op.add_column("users", sa.Column("uuid_id", sa.UUID(), nullable=True))

    # Update the temporary UUID column with mapped values
    op.execute(
        """
        UPDATE users u
        SET uuid_id = m.new_id
        FROM id_mapping m
        WHERE u.id = m.old_id
    """
    )

    # Drop the default value and sequence for users.id
    op.execute("ALTER TABLE users ALTER COLUMN id DROP DEFAULT")
    op.execute("DROP SEQUENCE IF EXISTS users_id_seq")

    # Drop the old id column and rename uuid_id to id
    op.drop_column("users", "id")
    op.execute("ALTER TABLE users RENAME COLUMN uuid_id TO id")

    # Make the id column NOT NULL and add a unique constraint
    op.execute("ALTER TABLE users ALTER COLUMN id SET NOT NULL")
    op.execute("ALTER TABLE users ADD CONSTRAINT users_id_key UNIQUE (id)")

    # Set the new default for users.id
    op.execute("ALTER TABLE users ALTER COLUMN id SET DEFAULT gen_random_uuid()")

    # Add a temporary UUID column to meeting_requests
    op.add_column(
        "meeting_requests",
        sa.Column(
            "uuid_user_a_id",
            sa.UUID(),
            nullable=True))

    # Update the temporary column with mapped values
    op.execute(
        """
        UPDATE meeting_requests mr
        SET uuid_user_a_id = m.new_id
        FROM id_mapping m
        WHERE mr.user_a_id = m.old_id
    """
    )

    # Drop the old user_a_id column and rename the temporary column
    op.drop_column("meeting_requests", "user_a_id")
    op.execute(
        "ALTER TABLE meeting_requests RENAME COLUMN uuid_user_a_id TO user_a_id")

    # Add the meeting_spots column
    op.add_column(
        "meeting_requests",
        sa.Column(
            "meeting_spots",
            sa.JSON(),
            nullable=True))

    # Recreate the foreign key constraint
    op.create_foreign_key(
        "meeting_requests_user_a_id_fkey",
        "meeting_requests",
        "users",
        ["user_a_id"],
        ["id"],
    )

    # Drop the temporary mapping table
    op.drop_table("id_mapping")


def downgrade():
    # Drop the foreign key constraint first
    op.drop_constraint(
        "meeting_requests_user_a_id_fkey",
        "meeting_requests",
        type_="foreignkey")

    # Create a temporary table to store the mapping of UUIDs to integers
    op.create_table(
        "id_mapping",
        sa.Column("uuid_id", sa.UUID(), nullable=False),
        sa.Column("int_id", sa.Integer(), nullable=False),
    )

    # Insert current user IDs into the mapping table
    op.execute(
        """
        INSERT INTO id_mapping (uuid_id, int_id)
        SELECT id, ROW_NUMBER() OVER (ORDER BY id)::INTEGER
        FROM users
    """
    )

    # Add a temporary integer column to users
    op.add_column("users", sa.Column("int_id", sa.Integer(), nullable=True))

    # Update the temporary integer column with mapped values
    op.execute(
        """
        UPDATE users u
        SET int_id = m.int_id
        FROM id_mapping m
        WHERE u.id = m.uuid_id
    """
    )

    # Drop the default value for users.id
    op.execute("ALTER TABLE users ALTER COLUMN id DROP DEFAULT")

    # Drop the old id column and rename int_id to id
    op.drop_column("users", "id")
    op.execute("ALTER TABLE users RENAME COLUMN int_id TO id")

    # Make the id column NOT NULL and add a unique constraint
    op.execute("ALTER TABLE users ALTER COLUMN id SET NOT NULL")
    op.execute("ALTER TABLE users ADD CONSTRAINT users_id_key UNIQUE (id)")

    # Create a new sequence for users.id
    op.execute("CREATE SEQUENCE users_id_seq")
    op.execute(
        "ALTER TABLE users ALTER COLUMN id SET DEFAULT nextval('users_id_seq')")

    # Add a temporary integer column to meeting_requests
    op.add_column(
        "meeting_requests",
        sa.Column(
            "int_user_a_id",
            sa.Integer(),
            nullable=True))

    # Update the temporary column with mapped values
    op.execute(
        """
        UPDATE meeting_requests mr
        SET int_user_a_id = m.int_id
        FROM id_mapping m
        WHERE mr.user_a_id = m.uuid_id
    """
    )

    # Drop the UUID user_a_id column and rename the temporary column
    op.drop_column("meeting_requests", "user_a_id")
    op.execute(
        "ALTER TABLE meeting_requests RENAME COLUMN int_user_a_id TO user_a_id")

    # Drop the meeting_spots column
    op.drop_column("meeting_requests", "meeting_spots")

    # Recreate the foreign key constraint
    op.create_foreign_key(
        "meeting_requests_user_a_id_fkey",
        "meeting_requests",
        "users",
        ["user_a_id"],
        ["id"],
    )

    # Drop the temporary mapping table
    op.drop_table("id_mapping")
