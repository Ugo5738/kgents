"""
Test helper functions.
"""
import uuid
from typing import Dict, Any
from datetime import datetime, timezone

from agent_management_service.models.agent import Agent, AgentStatus
from agent_management_service.models.agent_version import AgentVersion


def create_test_agent(user_id: uuid.UUID) -> Dict[str, Any]:
    """
    Create a dictionary representing a test agent.
    
    Args:
        user_id: UUID of the user who owns the agent
        
    Returns:
        Dictionary representation of an agent
    """
    return {
        "id": uuid.uuid4(),
        "name": f"Test Agent {uuid.uuid4().hex[:8]}",
        "description": "Test agent created for unit tests",
        "config": {"test": "config", "generated": True},
        "tags": ["test", "unit-test"],
        "status": AgentStatus.DRAFT,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }


def create_test_agent_version(agent_id: uuid.UUID, user_id: uuid.UUID, version_number: int = 1) -> Dict[str, Any]:
    """
    Create a dictionary representing a test agent version.
    
    Args:
        agent_id: UUID of the agent
        user_id: UUID of the user who created the version
        version_number: Version number
        
    Returns:
        Dictionary representation of an agent version
    """
    return {
        "id": uuid.uuid4(),
        "agent_id": agent_id,
        "version_number": version_number,
        "config_snapshot": {
            "test": "config",
            "version": version_number,
            "generated": True
        },
        "change_summary": f"Test version {version_number}",
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc)
    }


async def create_agent_in_db(db, user_id: uuid.UUID) -> Agent:
    """
    Create an agent in the database.
    
    Args:
        db: Database session
        user_id: UUID of the user who owns the agent
        
    Returns:
        Agent instance
    """
    agent_data = create_test_agent(user_id)
    agent = Agent(**agent_data)
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


async def create_agent_version_in_db(db, agent_id: uuid.UUID, user_id: uuid.UUID, version_number: int = 1) -> AgentVersion:
    """
    Create an agent version in the database.
    
    Args:
        db: Database session
        agent_id: UUID of the agent
        user_id: UUID of the user who created the version
        version_number: Version number
        
    Returns:
        AgentVersion instance
    """
    version_data = create_test_agent_version(agent_id, user_id, version_number)
    version = AgentVersion(**version_data)
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return version
