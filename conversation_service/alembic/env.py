# conversation_service/alembic/env.py

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

# --- Path Setup for Alembic ---
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
# Add the project root to the path (for shared)
sys.path.insert(0, str(project_root))

# Now we can safely import our project's modules
from conversation_service.config import settings
from shared.models.base import Base

# Import all models to ensure they're registered with Base.metadata
from conversation_service.models import *  # noqa: F401,F403

# --- Alembic Configuration ---
config = context.config

# Configure loggers from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the database URL for Alembic from our settings
config.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
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
    connectable = create_async_engine(str(settings.DATABASE_URL))
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
