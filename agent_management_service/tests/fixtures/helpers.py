"""
Helper functions for testing.
Provides utility functions for seeding test data and other common operations.
"""
import uuid
import json
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agent_management_service.models.agent import Agent
from agent_management_service.models.agent_version import AgentVersion


async def seed_test_user(db_session: AsyncSession, user_id: str = None, email: str = None, username: str = None) -> str:
    """
    Create a test user record directly in the auth.users table to satisfy foreign key constraints.
    Returns the created user's ID.
    
    Args:
        db_session: SQLAlchemy AsyncSession object
        user_id: Optional UUID string for the user ID (generated if not provided)
        email: Optional email address (generated if not provided)
        username: Optional username (generated if not provided)
    
    Returns:
        str: The UUID of the created user
    """
    if user_id is None:
        user_id = str(uuid.uuid4())
    
    if email is None:
        email = f"test_{user_id}@example.com"
        
    if username is None:
        username = f"testuser_{user_id[:8]}"
    
    # Create user metadata with the username
    user_meta_data = json.dumps({"username": username})
    app_meta_data = json.dumps({})
    
    # Ensure we have the auth.users table
    try:
        # Insert the user record into the auth.users table using raw SQL
        await db_session.execute(
            text(f"""
            INSERT INTO auth.users (
                id, 
                raw_user_meta_data,
                raw_app_meta_data,
                is_anonymous,
                created_at, 
                updated_at,
                role
            )
            VALUES (
                '{user_id}'::uuid,
                '{user_meta_data}'::jsonb,
                '{app_meta_data}'::jsonb,
                false,
                NOW(),
                NOW(),
                'authenticated'
            )
            ON CONFLICT (id) DO NOTHING
            """)
        )
        
        # Commit the transaction
        await db_session.commit()
        print(f"Created test user in auth.users: {user_id} | {username}")
        
    except Exception as e:
        print(f"Error creating test user: {e}")
        await db_session.rollback()
        raise
    
    return user_id


async def create_test_agent(db_session: AsyncSession, user_id: str = None, name: str = "Test Agent", 
                           description: str = "Test Agent Description", 
                           langflow_data: dict = None) -> Agent:
    """
    Create a test agent record in the database.
    
    Args:
        db_session: SQLAlchemy AsyncSession object
        user_id: User ID of the agent owner (created test user if not provided)
        name: Agent name
        description: Agent description
        langflow_data: Langflow configuration data (simple default if not provided)
        
    Returns:
        Agent: The created agent object
    """
    if user_id is None:
        user_id = await seed_test_user(db_session)
    
    if langflow_data is None:
        langflow_data = {
            "version": "1.0.0",
            "nodes": [],
            "edges": []
        }
    
    agent = Agent(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        name=name,
        description=description,
        is_active=True,
        langflow_data=langflow_data,
        status="draft",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db_session.add(agent)
    await db_session.flush()
    await db_session.commit()
    
    return agent


async def create_test_agent_version(db_session: AsyncSession, agent_id: uuid.UUID = None, 
                                  version: int = 1, langflow_data: dict = None) -> AgentVersion:
    """
    Create a test agent version record in the database.
    
    Args:
        db_session: SQLAlchemy AsyncSession object
        agent_id: Agent ID to associate with the version (creates a test agent if not provided)
        version: Version number
        langflow_data: Langflow configuration data (simple default if not provided)
        
    Returns:
        AgentVersion: The created agent version object
    """
    if agent_id is None:
        agent = await create_test_agent(db_session)
        agent_id = agent.id
    
    if langflow_data is None:
        langflow_data = {
            "version": "1.0.0",
            "nodes": [],
            "edges": []
        }
    
    agent_version = AgentVersion(
        id=uuid.uuid4(),
        agent_id=agent_id,
        version=version,
        langflow_data=langflow_data,
        created_at=datetime.utcnow()
    )
    
    db_session.add(agent_version)
    await db_session.flush()
    await db_session.commit()
    
    return agent_version
