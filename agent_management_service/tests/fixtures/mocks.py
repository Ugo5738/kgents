"""
Mock fixtures for testing.
Provides mock implementations of external dependencies like Auth Service client.
"""
import pytest_asyncio
from unittest.mock import AsyncMock
import uuid
import os
from typing import Dict, Any, Optional


class MockAuthResponse:
    """Mock response from Auth service validation endpoints."""
    def __init__(self, user_id: Optional[str] = None):
        self.user_id = user_id or str(uuid.uuid4())
        self.is_valid = True
        self.roles = ["user"]
        self.error = None


@pytest_asyncio.fixture
async def mock_auth_service_client():
    """
    Create a mock Auth Service client for testing that responds to token validation methods.
    The client will return a consistent user ID that we can use to pre-create database
    records to satisfy foreign key constraints.
    """
    # Get test user ID from environment or use a default
    test_user_id = os.environ.get("TEST_USER_ID", "00000000-0000-0000-0000-000000000001")
    
    # Create a mock auth service client
    mock_client = AsyncMock()
    
    # Configure the validate_token method to return our mock response
    mock_auth_response = MockAuthResponse(user_id=test_user_id)
    mock_client.validate_token = AsyncMock(return_value=mock_auth_response)
    
    # Add the test user ID as an attribute so tests can access it
    mock_client.test_user_id = test_user_id
    
    print(f"\nUsing mock Auth Service client with test user ID: {test_user_id}")
    
    return mock_client


class MockCrud:
    """Mock CRUD operations for when we need to bypass the database."""
    
    @staticmethod
    async def get_agent_by_id(*args, **kwargs):
        """Mock implementation of get_agent_by_id."""
        from agent_management_service.models.agent import Agent
        import uuid
        from datetime import datetime
        
        agent_id = kwargs.get('agent_id', str(uuid.uuid4()))
        
        return Agent(
            id=uuid.UUID(agent_id),
            user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            name="Test Agent",
            description="A test agent for unit tests",
            is_active=True,
            langflow_data={"version": "1.0.0", "nodes": [], "edges": []},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @staticmethod
    async def get_agent_version_by_id(*args, **kwargs):
        """Mock implementation of get_agent_version_by_id."""
        from agent_management_service.models.agent_version import AgentVersion
        import uuid
        from datetime import datetime
        
        version_id = kwargs.get('version_id', str(uuid.uuid4()))
        agent_id = kwargs.get('agent_id', str(uuid.uuid4()))
        
        return AgentVersion(
            id=uuid.UUID(version_id),
            agent_id=uuid.UUID(agent_id),
            version=1,
            langflow_data={"version": "1.0.0", "nodes": [], "edges": []},
            created_at=datetime.utcnow()
        )
    
    @staticmethod
    async def create_agent_in_db(*args, **kwargs):
        """Mock implementation of create_agent_in_db."""
        from agent_management_service.models.agent import Agent
        import uuid
        from datetime import datetime
        
        agent_in = kwargs.get('agent_in', None)
        if not agent_in:
            return None
            
        return Agent(
            id=uuid.uuid4(),
            user_id=uuid.UUID(agent_in.user_id) if hasattr(agent_in, 'user_id') else uuid.UUID("00000000-0000-0000-0000-000000000001"),
            name=agent_in.name if hasattr(agent_in, 'name') else "Test Agent",
            description=agent_in.description if hasattr(agent_in, 'description') else "Test description",
            is_active=True,
            langflow_data=agent_in.langflow_data if hasattr(agent_in, 'langflow_data') else {"version": "1.0.0", "nodes": [], "edges": []},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
