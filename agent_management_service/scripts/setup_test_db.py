"""
Script to create test database tables directly from SQLAlchemy models.
This is an alternative to using Alembic for test database setup.
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Add parent directory to path to allow imports
import sys
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

# Import the SQLAlchemy Base and models
from src.agent_management_service.db import Base
from src.agent_management_service.models import agent, agent_version

# Test database URL
DB_URL = "postgresql+psycopg://postgres:postgres@127.0.0.1:54322/agent_management_test_db"

async def setup_test_db():
    """Create tables in the test database directly from SQLAlchemy models."""
    print(f"Creating tables in test database: {DB_URL}")
    
    # Create engine
    engine = create_async_engine(DB_URL)
    
    async with engine.begin() as conn:
        # Drop existing tables if any
        await conn.run_sync(Base.metadata.drop_all)
        
        # Create auth schema
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS auth;"))
        
        # Create mock auth.users table
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

if __name__ == "__main__":
    asyncio.run(setup_test_db())
