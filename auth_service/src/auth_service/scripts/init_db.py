#!/usr/bin/env python
"""
Database Initialization Script

This script creates all tables defined in SQLAlchemy models for a fresh database.
It should be run when setting up a new development or test database.
"""
import asyncio
import logging
import sys
import os

# Add the src directory to path to allow imports
# This script should be run from the auth_service directory
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
sys.path.insert(0, src_path)

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.schema import CreateSchema

from auth_service.config import settings
from auth_service.db import Base, get_db
from auth_service.bootstrap import run_bootstrap

# Import all models to ensure they're registered with SQLAlchemy Base
from auth_service.models.role import Role
from auth_service.models.permission import Permission
from auth_service.models.role_permission import RolePermission
from auth_service.models.profile import Profile
from auth_service.models.user_role import UserRole
from auth_service.models.app_client import AppClient
from auth_service.models.app_client_role import AppClientRole
from auth_service.models.app_client_refresh_token import AppClientRefreshToken

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("db_init")


async def init_db():
    """
    Initialize database schema by creating all tables
    defined in SQLAlchemy models.
    """
    try:
        logger.info(f"Creating database schema in {settings.DATABASE_URL.split('@')[1].split('/')[1]}")
        
        # Create engine with same parameters as main application
        connect_args = {
            "application_name": "auth_service_init_db",
            "options": "-c timezone=UTC -c statement_timeout=10000",
        }
        
        engine = create_async_engine(
            settings.DATABASE_URL, 
            connect_args=connect_args,
            echo=True
        )
        
        async with engine.begin() as conn:
            logger.info("Dropping all existing tables (if any)...")
            await conn.run_sync(Base.metadata.drop_all)
            
            logger.info("Creating all tables...")
            await conn.run_sync(Base.metadata.create_all)
        
        # Run bootstrap process to create initial roles, permissions, etc.
        logger.info("Running bootstrap process to create initial data...")
        async for session in get_db():
            await run_bootstrap(session)
            break
        
        logger.info("Database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(init_db())
