"""
Script to create test database tables directly from SQLAlchemy models.

This script bypasses Alembic migrations for test environments by:
1. Reading the database URL from .env.test or environment variables
2. Creating all tables defined in SQLAlchemy models
3. Setting up mock Supabase auth tables for foreign key constraints

Usage:
    python scripts/setup_test_db.py [--force] [--no-env-file]

Options:
    --force      Drop existing tables before creating new ones
    --no-env-file  Don't load variables from .env.test file
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    print("dotenv not installed. Run: pip install python-dotenv")
    load_dotenv = lambda x: None

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Add parent directory to path to allow imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

# Import the SQLAlchemy Base and models
from src.agent_management_service.db import Base
from src.agent_management_service.models import agent, agent_version

# Default test database URL (used as fallback)
DEFAULT_DB_URL = "postgresql+psycopg://postgres:postgres@127.0.0.1:54322/agent_management_test_db"

def get_db_url(use_env_file: bool = True) -> str:
    """
    Get the database URL from environment variables or .env.test file.
    
    Args:
        use_env_file: Whether to load variables from .env.test file
        
    Returns:
        Database URL string
    """
    # Load from .env.test file if it exists and requested
    if use_env_file:
        env_file = Path(parent_dir) / ".env.test"
        if env_file.exists():
            load_dotenv(env_file)
            print(f"Loaded environment from {env_file}")
    
    # Get database URL from environment variables
    db_url = os.environ.get("AGENT_MANAGEMENT_SERVICE_DATABASE_URL")
    
    # Fall back to the default if not found
    if not db_url:
        print("Warning: AGENT_MANAGEMENT_SERVICE_DATABASE_URL not found in environment.")
        print(f"Using default test database URL: {DEFAULT_DB_URL}")
        db_url = DEFAULT_DB_URL
        
    return db_url

async def setup_test_db(db_url: str, force_drop: bool = False) -> bool:
    """
    Create tables in the test database directly from SQLAlchemy models.
    
    Args:
        db_url: Database URL to connect to
        force_drop: Whether to force dropping existing tables
        
    Returns:
        True if successful, False otherwise
    """
    print(f"Creating tables in test database: {db_url}")
    
    try:
        # Create engine
        engine = create_async_engine(db_url)
        
        async with engine.begin() as conn:
            if force_drop:
                print("Dropping existing tables...")
                # Drop existing tables if requested
                await conn.run_sync(Base.metadata.drop_all)
            
            # Create auth schema
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS auth;"))
            
            # Create mock auth.users table for foreign key constraints
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS auth.users (
                    id UUID PRIMARY KEY,
                    instance_id UUID,
                    aud VARCHAR,
                    role VARCHAR,
                    email VARCHAR,
                    encrypted_password VARCHAR,
                    created_at TIMESTAMP WITH TIME ZONE,
                    updated_at TIMESTAMP WITH TIME ZONE
                );
            """))
            
            # Create all tables from models
            await conn.run_sync(Base.metadata.create_all)
            
            # Verify tables were created
            result = await conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public';"
            ))
            tables = [row[0] for row in result.fetchall()]
            print(f"Created tables in database: {tables}")
        
        await engine.dispose()
        return True
    except SQLAlchemyError as e:
        print(f"Error setting up test database: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

async def main():
    """
    Main entry point for the script.
    Parse arguments and set up the test database.
    """
    parser = argparse.ArgumentParser(description="Set up test database for agent_management_service")
    parser.add_argument("--force", action="store_true", help="Force drop existing tables")
    parser.add_argument("--no-env-file", action="store_true", help="Don't load variables from .env.test file")
    
    args = parser.parse_args()
    
    db_url = get_db_url(not args.no_env_file)
    success = await setup_test_db(db_url, args.force)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
