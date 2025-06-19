#!/bin/bash
set -e

# Initialize database schema for auth service
echo "Creating database tables for auth_dev_db..."
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.schema import CreateSchema
from auth_service.db import Base
from auth_service.config import settings
from auth_service.models.role import Role
from auth_service.models.permission import Permission
from auth_service.models.role_permission import RolePermission
from auth_service.models.profile import Profile
from auth_service.models.user_role import UserRole
from auth_service.models.app_client import AppClient
from auth_service.models.app_client_role import AppClientRole
from auth_service.models.app_client_refresh_token import AppClientRefreshToken

async def init_db():
    print(f'Creating database tables in {settings.DATABASE_URL}')
    engine = create_async_engine(
        settings.DATABASE_URL, 
        echo=True,
        connect_args={
            'application_name': 'auth_service_init_db',
            'options': '-c timezone=UTC -c statement_timeout=10000',
        }
    )
    
    async with engine.begin() as conn:
        # Drop tables in case they exist
        await conn.run_sync(Base.metadata.drop_all)
        
        # Create schemas first
        try:
            print('Creating auth schema if it does not exist...')
            await conn.execute(CreateSchema('auth', if_not_exists=True))
            print('Auth schema created or already exists')
        except Exception as e:
            print(f'Error creating schema: {e}')
            raise
            
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    print('Database initialization completed!')

asyncio.run(init_db())
"

# Run bootstrap process to create initial data
echo "Running bootstrap process..."
python -c "
import asyncio
from auth_service.bootstrap import run_bootstrap
from auth_service.db import get_db

async def run_bootstrap_process():
    # Using the correct session manager from db.py
    async for session in get_db():
        success = await run_bootstrap(session)
        if success:
            print('Bootstrap process completed successfully')
        else:
            print('Bootstrap process failed')
            exit(1)
        break

asyncio.run(run_bootstrap_process())
"

echo "Database initialization and bootstrap completed successfully!"
