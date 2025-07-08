# auth_service/scripts/manage_db.py
import argparse
import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

# --- Script Setup ---
# Ensure the service's src directory is in the Python path
# This allows the script to be run from the service's root directory
service_dir = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(service_dir / "src"))

# --- SERVICE-SPECIFIC CONFIGURATION ---
# The only section you need to change when adapting to a new service.
# 1. Change these imports for each service
from auth_service.config import settings
from auth_service.db import Base, get_db

SERVICE_NAME = settings.PROJECT_NAME

# 2. Set these flags to control service-specific logic
IS_AUTH_SERVICE = True  # Enables special logic like copying the auth schema
HAS_BOOTSTRAP = True  # Set to True if the service has a bootstrap process

# Dynamically import the bootstrap function only if needed
if HAS_BOOTSTRAP:
    # 3. Adjust this import path if the bootstrap module is different
    from auth_service.bootstrap import run_bootstrap
# -----------------------------------------


# --- Generic Helper Functions (Service Agnostic) ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("manage_db")


def colored(text: str, color: str) -> str:
    """Applies ANSI color codes to text for better terminal output."""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "reset": "\033[0m",
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"


def run_command(command: str, check: bool = True):
    """Executes a shell command and streams its output."""
    logger.info(colored(f"--- Running: {command} ---", "yellow"))
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=service_dir,
    )
    for line in process.stdout:
        print(line, end="")
    process.wait()
    if check and process.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {process.returncode}")


def get_db_params(db_url: str) -> dict:
    """Extracts connection parameters from a database URL."""
    from urllib.parse import urlparse

    parsed = urlparse(str(db_url))
    return {
        "user": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname,
        "port": parsed.port,
        "dbname": parsed.path.lstrip("/"),
    }


# --- Core Database Operations (Service Agnostic Logic) ---
async def create_db(db_params: dict):
    """Creates the service-specific database if it doesn't exist."""
    db_name = db_params["dbname"]
    logger.info(f"Ensuring database '{db_name}' exists...")
    # Connect to the default 'postgres' db to run the create command
    conn_str_admin = f"postgresql+psycopg://{db_params['user']}:{db_params['password']}@{db_params['host']}:{db_params['port']}/postgres"
    try:
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
    conn_str_admin = f"postgresql+psycopg://{db_params['user']}:{db_params['password']}@{db_params['host']}:{db_params['port']}/postgres"
    # Terminate connections and drop
    run_command(
        f'psql "{conn_str_admin}" -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = \'{db_name}\';"',
        check=False,
    )
    run_command(f'psql "{conn_str_admin}" -c "DROP DATABASE IF EXISTS {db_name}"')
    logger.info(colored(f"Database '{db_name}' deleted.", "green"))


# --- Service-Specific Operations ---
async def copy_auth_schema(db_params: dict):
    """Copies the Supabase 'auth' schema using pg_dump."""
    if not IS_AUTH_SERVICE:
        logger.info("Not an auth service, skipping auth schema copy.")
        return
    logger.info("Copying Supabase 'auth' schema...")
    source_conn_str = f"postgresql+psycopg://{db_params['user']}:{db_params['password']}@{db_params['host']}:{db_params['port']}/postgres"
    dump_command = (
        f'pg_dump "{source_conn_str}" --schema-only --no-owner -n auth | '
        f'psql "{settings.DATABASE_URL}" --quiet'
    )
    run_command(dump_command)
    logger.info(colored("'auth' schema copied successfully.", "green"))


async def bootstrap_service():
    """Runs the service-specific bootstrap process."""
    if not HAS_BOOTSTRAP:
        logger.info("Service has no bootstrap process. Skipping.")
        return
    logger.info("Running application bootstrap...")
    try:
        async for session in get_db():
            await run_bootstrap(session)
            break
        logger.info(colored("Bootstrap process completed successfully.", "green"))
    except Exception as e:
        logger.error(colored(f"Bootstrap process failed: {e}", "red"), exc_info=True)
        raise


# --- Main Command Orchestrator ---
async def main():
    parser = argparse.ArgumentParser(
        description=f"{SERVICE_NAME} Database Management Tool"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "init",
        help="Fully initializes the database (create, copy schema, migrate, bootstrap).",
    )
    subparsers.add_parser(
        "recreate", help="Deletes and then fully initializes the database."
    )
    subparsers.add_parser("delete-db", help="Deletes the database entirely.")
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

    # Set PGPASSWORD for psql and pg_dump commands
    db_params = get_db_params(str(settings.DATABASE_URL))
    os.environ["PGPASSWORD"] = db_params["password"]

    try:
        if args.command == "init":
            await create_db(db_params)
            await copy_auth_schema(db_params)
            run_command("alembic upgrade head")
            await bootstrap_service()
        elif args.command == "recreate":
            await delete_db(db_params)
            await create_db(db_params)
            await copy_auth_schema(db_params)
            run_command("alembic upgrade head")
            await bootstrap_service()
        elif args.command == "delete-db":
            await delete_db(db_params)
        elif args.command == "create-migration":
            run_command(f'alembic revision --autogenerate -m "{args.message}"')
        elif args.command == "upgrade":
            run_command("alembic upgrade head")
        elif args.command == "downgrade":
            run_command(f"alembic downgrade -{args.step}")
        elif args.command == "verify":
            run_command("alembic check")

        print(colored("\nOperation completed successfully.", "green"))

    except Exception as e:
        logger.error(colored(f"\nOperation failed: {e}", "red"), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
