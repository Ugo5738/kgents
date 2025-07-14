"""
Database fixtures for testing.
Provides fixtures for test database setup, session management, and teardown.
"""
import os
import asyncio
import logging
from typing import AsyncGenerator, Generator, Optional

import pytest
import pytest_asyncio
from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from auth_service.config import settings
from auth_service.db import Base
from auth_service.logging_config import logger

# Global variable to hold the engine
_test_engine = None

# Global function to get or create the test engine
def get_test_engine():
    """
    Get or create the test database engine.
    Uses a global variable to ensure we only create one engine per test session.
    Overrides the database URL to use a local test database for running tests.
    """
    global _test_engine
    if _test_engine is None:
        # For testing, override the database URL to use a local PostgreSQL instance
        # This prevents connection errors when running tests outside of Docker
        
        # Try to determine the current user for PostgreSQL authentication
        # On macOS, PostgreSQL often uses the current system username for auth
        import getpass
        current_user = getpass.getuser()
        
        test_db_url = os.environ.get(
            "AUTH_SERVICE_TEST_DATABASE_URL",
            # Default to a local PostgreSQL connection with current user and no password
            f"postgresql+psycopg://{current_user}@localhost:5432/postgres"
        )
        
        logger.info(f"Creating test database engine with URL: {test_db_url}")
        _test_engine = create_async_engine(
            test_db_url,
            poolclass=NullPool,  # Use NullPool to avoid connection pooling issues in tests
            echo=(settings.LOGGING_LEVEL.upper() == "DEBUG"),  # Echo SQL if debug logging is enabled
            future=True,  # Use SQLAlchemy 2.0 style
            # Set search_path to include auth_service_data schema
            connect_args={"options": "-c search_path=auth_service_data,public"}
        )
    return _test_engine

# Create the session factory for tests
def get_test_session_factory():
    """
    Create a new session factory bound to the test engine.
    """
    engine = get_test_engine()
    return sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False
    )


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create and yield a single event loop for the test session."""
    # Create a new loop for the test session
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    
    # Set as current event loop to ensure all async code uses this loop
    asyncio.set_event_loop(loop)
    
    logger.info("Created new event loop for test session")
    
    try:
        yield loop
    finally:
        # Clean up resources and close the loop
        logger.info("Cleaning up event loop")
        pending = asyncio.all_tasks(loop=loop)
        if pending:
            logger.info(f"Found {len(pending)} pending tasks, waiting for completion")
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()
        logger.info("Event loop closed")


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    """
    Set up the test database once per test session.
    This creates the necessary tables and schema, including a mock of Supabase's auth.users table.
    """
    logger.info(f"Setting up test database with URL: {settings.DATABASE_URL}")
    
    # Get the test engine
    engine = get_test_engine()
    
    try:
        # Create database tables from SQLAlchemy models
        async with engine.begin() as conn:
            # First drop all existing tables to ensure a clean state
            logger.info("Dropping existing tables to ensure clean state")
            await conn.run_sync(Base.metadata.drop_all)
            
            # Create the auth schema required by Supabase references 
            logger.info("Creating auth schema for Supabase mock tables")
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS auth;"))
            
            # Create a minimal version of auth.users table that satisfies our foreign key constraints
            logger.info("Creating mock auth.users table")
            # This simulates the Supabase auth.users table in the test environment
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS auth.users (
                    id UUID PRIMARY KEY,
                    instance_id UUID,
                    aud VARCHAR,
                    role VARCHAR,
                    encrypted_password VARCHAR,
                    confirmation_token VARCHAR, 
                    email_confirmed_at TIMESTAMP WITH TIME ZONE,
                    invited_at TIMESTAMP WITH TIME ZONE,
                    confirmation_sent_at TIMESTAMP WITH TIME ZONE,
                    recovery_token VARCHAR,
                    recovery_sent_at TIMESTAMP WITH TIME ZONE,
                    email_change_token_new VARCHAR,
                    email_change VARCHAR,
                    email_change_sent_at TIMESTAMP WITH TIME ZONE,
                    last_sign_in_at TIMESTAMP WITH TIME ZONE,
                    raw_app_meta_data JSONB,
                    raw_user_meta_data JSONB,
                    is_super_admin BOOLEAN,
                    created_at TIMESTAMP WITH TIME ZONE,
                    updated_at TIMESTAMP WITH TIME ZONE,
                    phone VARCHAR NULL UNIQUE,
                    phone_confirmed_at TIMESTAMP WITH TIME ZONE,
                    phone_change VARCHAR NULL DEFAULT ''::character varying,
                    phone_change_token VARCHAR NULL DEFAULT ''::character varying,
                    phone_change_sent_at TIMESTAMP WITH TIME ZONE,
                    confirmed_at TIMESTAMP WITH TIME ZONE,
                    is_anonymous BOOLEAN DEFAULT false
                );
            """))
            
            # Create the auth_service_data schema if it doesn't exist
            logger.info("Creating auth_service_data schema")
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS auth_service_data;"))
            
            # Create all tables from models
            logger.info("Creating auth service tables from models")
            await conn.run_sync(Base.metadata.create_all)
            
            # Verify tables were created
            result = await conn.execute(text("""
                SELECT table_schema, table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'auth_service_data';
            """))
            tables = result.fetchall()
            logger.info(f"Created {len(tables)} tables in auth_service_data schema")
            
        logger.info("Test database setup complete")
        
        # Yield control back to the tests
        yield
    except Exception as e:
        logger.error(f"Error during test database setup: {e}")
        raise
    finally:
        # Clean up after tests are done
        logger.info("Tearing down test database")
        try:
            async with engine.begin() as conn:
                # Drop all tables
                logger.info("Dropping all auth_service_data tables")
                await conn.run_sync(Base.metadata.drop_all)
                
                # Drop the auth schema and all its tables
                logger.info("Dropping auth schema")
                await conn.execute(text("DROP SCHEMA IF EXISTS auth CASCADE;"))
                
                logger.info("Test database teardown complete")
        except Exception as e:
            logger.error(f"Error during test database teardown: {e}")
            # Don't raise here as we're in cleanup and want to avoid masking test errors


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create and yield a new database session for each test.
    The session is rolled back after each test to maintain isolation.
    This ensures changes made by one test do not affect other tests.
    """
    # Get the session factory
    test_session_factory = get_test_session_factory()
    
    # Create a new session for each test
    logger.debug("Creating new test database session")
    async with test_session_factory() as session:
        # Start a nested transaction (savepoint)
        logger.debug("Starting transaction with savepoint for test isolation")
        await session.begin_nested()
        
        try:
            # Yield the session for the test to use
            yield session
        except Exception as e:
            logger.error(f"Error during test execution with DB session: {e}")
            raise
        finally:
            # Always roll back the transaction after the test
            logger.debug("Rolling back transaction to maintain test isolation")
            await session.rollback()
