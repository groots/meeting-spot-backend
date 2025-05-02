#!/usr/bin/env python3
"""
Setup Migration Template Script

This script sets up a custom migration template for Alembic to ensure
all migrations follow best practices and are idempotent.
"""
import configparser
import logging
import os
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("setup_template")


def setup_migration_template():
    """Configure Alembic to use our custom migration template."""
    # Paths
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    example_template = os.path.join(migrations_dir, "migration_template.py.example")
    template_dir = os.path.join(migrations_dir, "templates")
    template_path = os.path.join(template_dir, "migration_template.py.mako")
    alembic_ini_path = os.path.join(migrations_dir, "alembic.ini")
    main_alembic_ini_path = os.path.join(os.path.dirname(__file__), "alembic.ini")

    # Create templates directory if it doesn't exist
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)
        logger.info(f"Created directory: {template_dir}")

    # Copy the example template to the templates directory
    if os.path.exists(example_template):
        shutil.copy2(example_template, template_path)
        logger.info(f"Copied migration template to: {template_path}")
    else:
        logger.error(f"Template file not found: {example_template}")
        logger.error("Please ensure you have the migration_template.py.example file in your migrations directory")
        return False

    # Update alembic.ini to use the custom template
    for ini_path in [alembic_ini_path, main_alembic_ini_path]:
        if os.path.exists(ini_path):
            # Read the config
            config = configparser.ConfigParser()
            config.read(ini_path)

            # Update the file_template setting
            if "alembic" in config:
                # Set the template directory
                if template_dir.startswith(os.path.dirname(ini_path)):
                    # Use relative path if template is under the ini file directory
                    rel_template_dir = os.path.relpath(template_dir, os.path.dirname(ini_path))
                    template_setting = os.path.join(rel_template_dir, "migration_template.py.mako")
                else:
                    # Use absolute path otherwise
                    template_setting = template_path

                config["alembic"]["file_template"] = "%%(rev)s_%%(slug)s"  # Use standardized file naming
                config["alembic"]["script_location"] = "migrations"  # Ensure script location is set
                logger.info(f"Updated alembic configuration in {ini_path}")

                # Write the changes
                with open(ini_path, "w") as configfile:
                    config.write(configfile)
                logger.info(f"Successfully updated {ini_path}")
            else:
                logger.error(f"Invalid alembic configuration in {ini_path}")

    logger.info("Migration template setup complete!")
    logger.info(
        """
Next steps:
1. Run 'flask db migrate' to create a new migration using the template
2. Review the generated migration for best practices
3. Apply the migration with 'flask db upgrade' or './deploy_migrations.sh'
    """
    )

    return True


if __name__ == "__main__":
    setup_migration_template()
