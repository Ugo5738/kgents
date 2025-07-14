#!/usr/bin/env python
# auth_service/scripts/manage_db.py

"""
Database management CLI for the Authentication Service.
"""
import argparse
import asyncio
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# --- Path Setup ---
service_dir = Path(__file__).parent.parent.absolute()
project_root = service_dir.parent
sys.path.insert(0, str(service_dir / "src"))
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

from auth_service.bootstrap import run_bootstrap
from auth_service.db import close_engine, get_engine, reset_session_factory
from auth_service.supabase_client import close_supabase_clients, init_supabase_clients


# --- Standalone Configuration ---
class StandaloneConfig:
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, ADMIN_DB_NAME, PROJECT_NAME = (
        "localhost",
        54322,
        "postgres",
        "postgres",
        "auth_dev_db",
        "postgres",
        "Authentication Service",
    )


config = StandaloneConfig()

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
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=service_dir,
            bufsize=1,
        )
        for line in iter(process.stdout.readline, ""):
            print(line, end="")
        process.wait()
        if check and process.returncode != 0:
            raise RuntimeError(f"Command failed with exit code {process.returncode}")
    except Exception as e:
        logger.error(
            colored(f"An error occurred while running the command: {e}", "red")
        )
        raise


def get_db_params(args: argparse.Namespace) -> Dict[str, any]:
    return {
        "host": args.host or config.DB_HOST,
        "port": args.port or config.DB_PORT,
        "user": args.user or config.DB_USER,
        "password": args.password or config.DB_PASSWORD,
        "dbname": args.dbname or config.DB_NAME,
    }


def set_db_url_env(db_params: Dict[str, any]):
    os.environ["AUTH_SERVICE_DATABASE_URL"] = (
        f"postgresql+psycopg://{db_params['user']}:{db_params['password']}@{db_params['host']}:{db_params['port']}/{db_params['dbname']}"
    )


def check_command(cmd: str):
    if not shutil.which(cmd):
        logger.error(
            colored(
                f"Command not found: '{cmd}'. Please ensure it is installed and in your PATH.",
                "red",
            )
        )
        raise FileNotFoundError(f"Required command '{cmd}' not found.")


def create_db(db_params: Dict):
    logger.info(f"Attempting to create database '{db_params['dbname']}'...")
    run_command(
        f"psql -h {db_params['host']} -p {db_params['port']} -U {db_params['user']} -d {config.ADMIN_DB_NAME} -c 'CREATE DATABASE {db_params['dbname']}'",
        check=False,
    )
    logger.info(
        colored(f"Database '{db_params['dbname']}' created or already exists.", "green")
    )


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


async def bootstrap_service():
    logger.info("Running service data bootstrap...")
    # Bootstrap needs its own Supabase client initialized with the correct DB URL
    # which is set by set_db_url_env before main logic runs.
    await init_supabase_clients()

    # Directly override the database connection with the correct database
    db_url = os.environ.get("AUTH_SERVICE_DATABASE_URL", "")

    # Ensure it's using auth_dev_db, not postgres database
    if "/postgres" in db_url and "/auth_dev_db" not in db_url:
        new_db_url = db_url.replace("/postgres", "/auth_dev_db")
        logger.info(
            f"Overriding DATABASE_URL for bootstrap to use auth_dev_db: {new_db_url}"
        )
        os.environ["AUTH_SERVICE_DATABASE_URL"] = new_db_url

    # Reset any existing database connections
    await reset_db_connections()

    # Create a fresh session with direct connection to auth_dev_db
    engine = create_async_engine(
        os.environ["AUTH_SERVICE_DATABASE_URL"],
        pool_pre_ping=True,
        connect_args={"options": "-c search_path=auth_service_data,public"},
    )
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    session = session_factory()

    # Explicitly set search path for this session to ensure schema visibility
    await session.execute(text("SET search_path TO auth_service_data, public"))

    try:
        logger.info("Verifying table access before bootstrap...")
        roles_check = await session.execute(
            text("SELECT count(*) FROM auth_service_data.roles")
        )
        roles_count = roles_check.scalar()
        logger.info(f"Found {roles_count} rows in roles table")

        # Now run bootstrap with the verified connection
        await run_bootstrap(session)
        await session.commit()
        logger.info(colored("Bootstrap complete.", "green"))
    except Exception as e:
        await session.rollback()
        logger.error(f"Bootstrap failed: {e}", exc_info=True)
        raise
    finally:
        await session.close()
        await close_supabase_clients()


async def recreate_environment(db_params: Dict):
    """
    Stops, resets, and restarts the entire Supabase stack, then migrates and bootstraps the database.
    This is the definitive way to get a clean slate.
    """
    logger.info("--- Stopping Supabase stack for a full reset ---")
    run_command("supabase stop --no-backup")
    logger.info(colored("Supabase stack stopped.", "green"))

    time.sleep(2)

    logger.info("--- Starting a fresh Supabase stack ---")
    run_command("supabase start")
    logger.info(colored("Fresh Supabase stack is running.", "green"))

    time.sleep(5)

    # Create our application-specific database
    logger.info("--- Creating application database ---")
    create_db(db_params)

    # Create custom schema inside our new database
    logger.info("--- Creating application schema 'auth_service_data' ---")
    run_command(
        f"psql -h {db_params['host']} -p {db_params['port']} -U {db_params['user']} -d {db_params['dbname']} -c 'CREATE SCHEMA IF NOT EXISTS auth_service_data'"
    )

    reset_migrations()
    run_command("alembic revision --autogenerate -m 'Initial schema'")
    run_command("alembic upgrade head")

    # Verify the tables were created before bootstrapping
    logger.info("--- Verifying database schema before bootstrap ---")
    run_command(
        f"psql -h {db_params['host']} -p {db_params['port']} -U {db_params['user']} -d {db_params['dbname']} -c '\\dt auth_service_data.*'"
    )

    # Make sure connection pools are fully reset before bootstrap
    logger.info("--- Resetting connection pools before bootstrap ---")
    await reset_db_connections()

    # Now run bootstrap with fresh connections
    await bootstrap_service()


async def reset_db_connections():
    """
    Properly reset database connections to ensure a clean state.
    This helps prevent transaction visibility issues between migration and bootstrap.
    """
    # First close any existing engine connections
    logger.info("Closing any existing database connections")
    await close_engine()

    # Reset the session factory to force recreation
    reset_session_factory()

    # Get a fresh engine connection
    engine = get_engine()

    # Test the connection to ensure it works
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT 1"))
        logger.info(f"Database connection test: {result.scalar() == 1}")

    logger.info("Database connections have been reset")


# --- Main Command Orchestrator ---
async def main():
    parser = argparse.ArgumentParser(
        description=f"{config.PROJECT_NAME} Database Management Tool"
    )
    parser.add_argument("--host", help="DB host")
    parser.add_argument("--port", type=int, help="DB port")
    parser.add_argument("--user", help="DB user")
    parser.add_argument("--password", help="DB password")
    parser.add_argument("--dbname", help="DB name")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "recreate",
        help="Stop, reset, and re-initialize the entire Supabase stack and database.",
    )
    create_mig_parser = subparsers.add_parser(
        "create-migration", help="Create a new Alembic migration."
    )
    create_mig_parser.add_argument(
        "-m", "--message", required=True, help="Migration message."
    )
    upgrade_parser = subparsers.add_parser("upgrade", help="Apply migrations.")
    upgrade_parser.add_argument(
        "-r", "--revision", default="head", help="Revision to upgrade to."
    )

    args = parser.parse_args()
    db_params = get_db_params(args)
    os.environ["PGPASSWORD"] = db_params["password"]
    load_dotenv(dotenv_path=service_dir / ".env.dev", override=True)
    set_db_url_env(db_params)

    try:
        if args.command == "recreate":
            await recreate_environment(db_params)
        elif args.command == "create-migration":
            run_command(f'alembic revision --autogenerate -m "{args.message}"')
        elif args.command == "upgrade":
            run_command(f"alembic upgrade {args.revision}")
        logger.info(
            colored(f"\nOperation '{args.command}' completed successfully.", "green")
        )
    except Exception as e:
        logger.error(colored(f"\nOperation failed: {e}", "red"), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
