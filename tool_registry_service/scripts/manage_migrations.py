#!/usr/bin/env python
"""
Migration management script for the Tool Registry Service.

This script helps manage database migrations for the Tool Registry Service,
providing a consistent approach to generating and applying migrations
across different environments.

Usage:
    python scripts/manage_migrations.py generate "description_of_changes"
    python scripts/manage_migrations.py upgrade [--revision=head] [--env=dev|prod]
    python scripts/manage_migrations.py downgrade [--revision=base] [--env=dev|prod]
    python scripts/manage_migrations.py create-db [--env=dev|prod]
    python scripts/manage_migrations.py drop-db [--env=dev|prod]
    python scripts/manage_migrations.py reset-db [--env=dev|prod]
"""

import argparse
import asyncio
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Add project root to python path
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.append(str(PROJECT_ROOT))

# Import settings to ensure environment is loaded
from src.tool_registry_service.config import settings

# Database environment configurations
ENVIRONMENT_CONFIGS = {
    "dev": {
        "env_file": ".env.dev",
        "admin_db_url": "postgresql+psycopg://postgres:postgres@supabase_db_kgents:5432/tool_registry_dev_db",
    },
    "prod": {
        "env_file": ".env.prod",
        "admin_db_url": "postgresql+psycopg://postgres:postgres@supabase_db_kgents:5432/tool_registry_prod_db",
    },
}


def get_database_url(environment: str) -> str:
    """Get the database URL for the specified environment."""
    if environment not in ENVIRONMENT_CONFIGS:
        print(f"Error: Unknown environment '{environment}'. Use 'dev' or 'prod'.")
        sys.exit(1)

    # Load the appropriate .env file
    env_file = ENVIRONMENT_CONFIGS[environment]["env_file"]
    env_path = PROJECT_ROOT / env_file

    if not env_path.exists():
        print(
            f"Warning: Environment file {env_file} not found. Using default settings."
        )
        return settings.DATABASE_URL

    # Load environment variables from the file
    load_dotenv(env_path)

    # Get the DATABASE_URL from the loaded environment
    db_url = os.environ.get("TOOL_REGISTRY_SERVICE_DATABASE_URL")
    if not db_url:
        print(f"Warning: DATABASE_URL not found in {env_file}. Using default settings.")
        return settings.DATABASE_URL

    return db_url


def get_admin_db_url(environment: str) -> str:
    """Get the admin database URL for the specified environment."""
    return ENVIRONMENT_CONFIGS[environment]["admin_db_url"]


def run_alembic_command(command, *args, **kwargs):
    """Run an alembic command with the given arguments."""
    # Get the environment
    environment = kwargs.pop("environment", "dev")
    
    # Get the database URL for the environment
    db_url = get_database_url(environment)
    
    # Ensure we're using psycopg and not asyncpg for all alembic operations
    db_url_str = str(db_url)
    if not db_url_str.startswith('postgresql+psycopg://') and db_url_str.startswith('postgresql'):
        db_url_str = db_url_str.replace('postgresql://', 'postgresql+psycopg://')
        if 'postgresql+asyncpg' in db_url_str:
            db_url_str = db_url_str.replace('postgresql+asyncpg', 'postgresql+psycopg')
            
    print(f"Using database: {db_url_str}")
    
    # Force the DATABASE_URL environment variable to use the correct driver
    os.environ['DATABASE_URL'] = db_url_str
    
    # Set the correct working directory
    current_dir = os.getcwd()
    
    # Build the alembic command
    alembic_command = ["alembic", command] + list(args)
    
    # Run the alembic command
    result = subprocess.run(
        alembic_command,
        cwd=PROJECT_ROOT,
        env=os.environ,
        capture_output=kwargs.get("capture_output", False),
        text=True,
    )

    if result.returncode != 0:
        print(f"Error executing alembic command: {result.stderr}")
        sys.exit(result.returncode)

    return result


def generate_migration(message, environment="dev"):
    """Generate a new migration with auto-detect of schema changes."""
    print(f"Generating migration: {message} (Environment: {environment})")
    run_alembic_command("revision", "--autogenerate", "-m", message, environment=environment)
    print("Migration generated successfully.")
    print("\nTo apply the migration, run:")
    print(f"  python scripts/manage_migrations.py upgrade --env={environment}")


def upgrade_database(revision="head", environment="dev"):
    """Upgrade the database to the specified revision."""
    print(f"Upgrading database to revision: {revision} (Environment: {environment})")
    run_alembic_command("upgrade", revision, environment=environment)
    print("Database upgraded successfully.")


def downgrade_database(revision="-1", environment="dev"):
    """Downgrade the database to the specified revision."""
    print(f"Downgrading database to revision: {revision} (Environment: {environment})")
    run_alembic_command("downgrade", revision, environment=environment)
    print("Database downgraded successfully.")


def show_current_revision(environment="dev"):
    """Show the current revision of the database."""
    print(f"Current revision (Environment: {environment}):")
    result = run_alembic_command("current", environment=environment, capture_output=True)
    print(result.stdout)


def show_migration_history(environment="dev"):
    """Show the migration history."""
    print(f"Migration history (Environment: {environment}):")
    run_alembic_command("history", environment=environment)


async def create_database(environment="dev"):
    """Create a database if it doesn't exist for the specified environment."""
    # Get the database URL for the environment
    db_url = get_database_url(environment)
    admin_db_url = get_admin_db_url(environment)

    # Extract database name from URL
    db_url_str = str(db_url)
    db_name = re.search(r"/([^/]+)$", db_url_str).group(1)

    print(f"Creating database: {db_name} (Environment: {environment})")
    # Connect to admin database
    engine = create_async_engine(admin_db_url, isolation_level="AUTOCOMMIT")

    try:
        # Check if database exists
        async with engine.connect() as conn:
            result = await conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
            )
            database_exists = result.scalar() is not None

            if not database_exists:
                print(f"Database {db_name} doesn't exist. Creating...")
                await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                print(f"Database {db_name} created successfully.")
            else:
                print(f"Database {db_name} already exists.")
    except Exception as e:
        print(f"Error creating database: {e}")
        raise
    finally:
        await engine.dispose()


async def drop_database(environment="dev"):
    """Drop a database if it exists for the specified environment."""
    # Get the database URL for the environment
    db_url = get_database_url(environment)
    admin_db_url = get_admin_db_url(environment)

    # Extract database name from URL
    db_url_str = str(db_url)
    db_name = re.search(r"/([^/]+)$", db_url_str).group(1)

    print(f"Dropping database: {db_name} (Environment: {environment})")

    # Connect to admin database
    engine = create_async_engine(admin_db_url, isolation_level="AUTOCOMMIT")

    try:
        # Terminate all connections to the database
        async with engine.connect() as conn:
            await conn.execute(
                text(
                    f"""SELECT pg_terminate_backend(pg_stat_activity.pid) 
                    FROM pg_stat_activity 
                    WHERE pg_stat_activity.datname = '{db_name}' 
                    AND pid <> pg_backend_pid();"""
                )
            )

            # Check if database exists
            result = await conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
            )
            database_exists = result.scalar() is not None

            if database_exists:
                await conn.execute(text(f'DROP DATABASE "{db_name}"'))
                print(f"Database {db_name} dropped successfully.")
            else:
                print(f"Database {db_name} does not exist, nothing to drop.")
    except Exception as e:
        print(f"Error dropping database: {e}")
        raise
    finally:
        await engine.dispose()


def main():
    """Parse arguments and run appropriate commands."""
    parser = argparse.ArgumentParser(
        description="Tool Registry Service migration management"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Common arguments for all commands
    env_arg = {
        "--env": {
            "default": "dev",
            "choices": ["dev", "prod"],
            "help": "Environment to target (dev or prod)",
        }
    }

    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate a new migration")
    generate_parser.add_argument("message", help="Description of the migration")
    generate_parser.add_argument(
        "--env",
        default="dev",
        choices=["dev", "prod"],
        help="Environment to target (dev or prod)",
    )

    # Upgrade command
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade the database")
    upgrade_parser.add_argument(
        "--revision", default="head", help="Revision to upgrade to (default: head)"
    )
    upgrade_parser.add_argument(
        "--env",
        default="dev",
        choices=["dev", "prod"],
        help="Environment to target (dev or prod)",
    )

    # Downgrade command
    downgrade_parser = subparsers.add_parser("downgrade", help="Downgrade the database")
    downgrade_parser.add_argument(
        "--revision", default="-1", help="Revision to downgrade to (default: -1)"
    )
    downgrade_parser.add_argument(
        "--env",
        default="dev",
        choices=["dev", "prod"],
        help="Environment to target (dev or prod)",
    )

    # Current command
    current_parser = subparsers.add_parser("current", help="Show current revision")
    current_parser.add_argument(
        "--env",
        default="dev",
        choices=["dev", "prod"],
        help="Environment to target (dev or prod)",
    )

    # History command
    history_parser = subparsers.add_parser("history", help="Show migration history")
    history_parser.add_argument(
        "--env",
        default="dev",
        choices=["dev", "prod"],
        help="Environment to target (dev or prod)",
    )

    # Create database command
    create_db_parser = subparsers.add_parser(
        "create-db", help="Create database if it doesn't exist"
    )
    create_db_parser.add_argument(
        "--env",
        default="dev",
        choices=["dev", "prod"],
        help="Environment to target (dev or prod)",
    )

    # Drop database command
    drop_db_parser = subparsers.add_parser("drop-db", help="Drop database if it exists")
    drop_db_parser.add_argument(
        "--env",
        default="dev",
        choices=["dev", "prod"],
        help="Environment to target (dev or prod)",
    )

    # Reset database command (drop and recreate)
    reset_db_parser = subparsers.add_parser(
        "reset-db", help="Reset database (drop and recreate)"
    )
    reset_db_parser.add_argument(
        "--env",
        default="dev",
        choices=["dev", "prod"],
        help="Environment to target (dev or prod)",
    )

    args = parser.parse_args()

    # Default to dev environment if not specified
    environment = getattr(args, "env", "dev")

    if args.command == "generate":
        generate_migration(args.message, environment)
    elif args.command == "upgrade":
        upgrade_database(args.revision, environment)
    elif args.command == "downgrade":
        downgrade_database(args.revision, environment)
    elif args.command == "current":
        show_current_revision(environment)
    elif args.command == "history":
        show_migration_history(environment)
    elif args.command == "create-db":
        asyncio.run(create_database(environment))
    elif args.command == "drop-db":
        asyncio.run(drop_database(environment))
    elif args.command == "reset-db":
        asyncio.run(drop_database(environment))
        asyncio.run(create_database(environment))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
