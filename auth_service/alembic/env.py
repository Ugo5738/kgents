# auth_service/alembic/env.py

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# --- Path Setup for Alembic ---
# This ensures that Alembic can find all the necessary modules from both
# the service's `src` directory and the project's shared `shared` directory.
service_dir = Path(__file__).parent.parent.absolute()
project_root = service_dir.parent

# Add the service's own source code to the path
sys.path.insert(0, str(service_dir / "src"))
# Add the shared library to the path
sys.path.insert(0, str(project_root))

# Now we can safely import our project's modules
from auth_service.config import settings
from auth_service.db import Base

# Import all models to ensure they're registered with Base.metadata
from auth_service.models import *

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


# --- Ignore the 'auth' schema during autogeneration ---
def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and object.schema == "auth":
        return False
    else:
        return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,  # Recommended when using include_object
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(
        str(settings.DATABASE_URL),
        poolclass=pool.NullPool,
        connect_args={"options": "-c search_path=auth_service_data,public"},
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
