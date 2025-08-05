# auth_service/alembic/env.py

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# --- Path Setup for Alembic ---
# This ensures that Alembic can find all the necessary modules from both
# the service's `src` directory and the project's shared `shared` directory.
service_dir = Path(__file__).parent.parent.absolute()
project_root = service_dir.parent

# Load the development environment variables from the .env.dev file
dotenv_path = service_dir / ".env.dev"
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path, override=True)
else:
    print(f"Warning: .env.dev file not found at {dotenv_path}")

# Add the service's own source code to the path
sys.path.insert(0, str(service_dir / "src"))
# Add the shared library to the path
sys.path.insert(0, str(project_root))

# Now we can safely import our project's modules
from agent_deployment_service.config import settings
from agent_deployment_service.db import Base

# Import all models to ensure they're registered with Base.metadata
from agent_deployment_service.models import *

# --- Alembic Configuration ---
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the database URL for Alembic from our settings
config.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL))

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_async_engine(settings.DATABASE_URL)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
