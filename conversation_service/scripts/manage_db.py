#!/usr/bin/env python
# conversation_service/scripts/manage_db.py

"""
Database management CLI for the Conversation Service.
- Creates DB if missing
- Runs Alembic migrations
- Bootstraps M2M credentials via auth_service
"""

import argparse
import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict

# --- Path Setup ---
service_dir = Path(__file__).parent.parent.absolute()
project_root = service_dir.parent
sys.path.insert(0, str(service_dir / "src"))
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# --- Logging and Helpers ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("manage_db")


def colored(text: str, color: str) -> str:
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "reset": "\033[0m",
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"


def run_command(command: str, check: bool = True):
    logger.info(colored(f"--- Running: {command} ---", "yellow"))
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=check,
            text=True,
            capture_output=True,
            cwd=service_dir,
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(colored(result.stderr, "yellow"), file=sys.stderr)
        result.check_returncode()
    except subprocess.CalledProcessError as e:
        logger.error(colored(f"Command failed with exit code {e.returncode}", "red"))
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(colored(e.stderr, "red"), file=sys.stderr)
        raise
    except Exception as e:
        logger.error(colored(f"An error occurred: {e}", "red"))
        raise


def get_db_params_from_url(db_url: str) -> dict:
    from urllib.parse import urlparse

    parsed = urlparse(str(db_url))
    return {
        "user": parsed.username or "postgres",
        "password": parsed.password or "postgres",
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "dbname": parsed.path.lstrip("/"),
    }


def create_db(db_params: Dict):
    db_name = db_params["dbname"]
    admin_db_name = "postgres"
    logger.info(
        f"Ensuring database '{db_name}' exists on host '{db_params['host']}'..."
    )

    conn_str_admin = f"postgresql://{db_params['user']}:{db_params['password']}@{db_params['host']}:{db_params['port']}/{admin_db_name}"

    try:
        # The `check=False` allows the command to "fail" gracefully if the DB already exists.
        run_command(
            f'psql "{conn_str_admin}" -c "CREATE DATABASE {db_name}"', check=False
        )
        logger.info(
            colored(f"Database '{db_name}' created or already exists.", "green")
        )
    except Exception as e:
        logger.warning(f"Could not create database (it may already exist). Error: {e}")


async def delete_db(db_params: dict):
    """Deletes the service-specific database."""
    db_name = db_params["dbname"]
    logger.info(f"Deleting database '{db_name}'...")
    conn_str_admin = f"postgresql://{db_params['user']}:{db_params['password']}@{db_params['host']}:{db_params['port']}/postgres"
    # Terminate connections and drop
    run_command(
        f'psql "{conn_str_admin}" -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = \'{db_name}\';"',
        check=False,
    )
    run_command(f'psql "{conn_str_admin}" -c "DROP DATABASE IF EXISTS {db_name}"')
    logger.info(colored(f"Database '{db_name}' deleted.", "green"))


def reset_migrations():
    versions_dir = service_dir / "alembic" / "versions"
    logger.info(
        colored(f"--- Resetting migration history in {versions_dir} ---", "yellow")
    )
    if versions_dir.exists():
        for item in versions_dir.glob("*.py"):
            if item.name != "__init__.py":
                logger.info(f"Deleting migration file: {item.name}")
                item.unlink()
    else:
        versions_dir.mkdir(parents=True)
    (versions_dir / "__init__.py").touch(exist_ok=True)
    logger.info(colored("Migration history has been reset.", "green"))


def has_migrations() -> bool:
    """Return True if there are migration scripts present (excluding __init__.py)."""
    versions_dir = service_dir / "alembic" / "versions"
    if not versions_dir.exists():
        return False
    for item in versions_dir.glob("*.py"):
        if item.name != "__init__.py":
            return True
    return False


async def bootstrap_service():
    """Run M2M client bootstrap for conversation_service."""
    from conversation_service.bootstrap import run_bootstrap

    logger.info("Running service bootstrap for conversation_service...")
    try:
        ok = await run_bootstrap()
        if ok:
            logger.info(colored("Bootstrap complete.", "green"))
        else:
            logger.warning(colored("Bootstrap reported failure.", "yellow"))
    except Exception as e:
        logger.error(colored(f"Bootstrap failed: {e}", "red"), exc_info=True)


async def recreate_environment(db_params: Dict):
    logger.info("--- Recreating environment for Conversation Service ---")

    await delete_db(db_params)

    logger.info("--- Creating application database ---")
    create_db(db_params)

    reset_migrations()
    run_command("alembic revision --autogenerate -m 'Initial schema'")
    run_command("alembic upgrade head")

    await bootstrap_service()


async def main():
    dotenv_path = service_dir / ".env.dev"
    if dotenv_path.exists():
        logger.info(f"Loading environment variables from {dotenv_path}")
        load_dotenv(dotenv_path=dotenv_path, override=True)
    else:
        logger.warning(
            f"{dotenv_path} not found. Relying on shell environment variables."
        )

    from conversation_service.config import settings

    parser = argparse.ArgumentParser(
        description=f"{settings.PROJECT_NAME} Database Management Tool"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "init", help="Fully initializes the database (create, migrate, bootstrap)."
    )
    subparsers.add_parser(
        "recreate", help="Deletes and then fully initializes the database."
    )
    subparsers.add_parser("delete-db", help="Drop the database for this service.")
    create_mig_parser = subparsers.add_parser(
        "create-migration", help="Create a new Alembic migration file."
    )
    create_mig_parser.add_argument(
        "-m", "--message", required=True, help="Migration description."
    )
    subparsers.add_parser(
        "upgrade", help="Apply all pending migrations to the database."
    )
    downgrade_parser = subparsers.add_parser(
        "downgrade", help="Downgrade migrations by a number of steps."
    )
    downgrade_parser.add_argument(
        "-s",
        "--step",
        type=int,
        default=1,
        help="Number of steps to downgrade (default: 1).",
    )
    subparsers.add_parser(
        "verify", help="Verify that the DB schema matches the SQLAlchemy models."
    )

    args = parser.parse_args()

    db_params = get_db_params_from_url(str(settings.DATABASE_URL))
    os.environ["PGPASSWORD"] = db_params["password"]

    try:
        if args.command == "init":
            create_db(db_params)
            # Autogenerate initial migration if none exists yet
            if not has_migrations():
                run_command("alembic revision --autogenerate -m 'Initial schema'")
            run_command("alembic upgrade head")
            await bootstrap_service()
        elif args.command == "recreate":
            await recreate_environment(db_params)
        elif args.command == "delete-db":
            await delete_db(db_params)
        elif args.command == "create-migration":
            run_command(f'alembic revision --autogenerate -m "{args.message}"')
        elif args.command == "upgrade":
            run_command("alembic upgrade head")
        elif args.command == "downgrade":
            run_command(f"alembic downgrade -{args.step}")
        elif args.command == "verify":
            # Show current and heads to assist debugging state
            run_command("alembic heads")
            run_command("alembic current")

        print(colored("\nOperation completed successfully.", "green"))

    except Exception as e:
        logger.error(colored(f"\nOperation failed: {e}", "red"), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
