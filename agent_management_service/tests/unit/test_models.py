"""
Unit tests for database models.
"""
import pytest
from sqlalchemy import select
from uuid import UUID, uuid4

from agent_management_service.models import Agent, AgentVersion
from agent_management_service.models.agent import AgentStatus


class TestAgentModel:
    """Test suite for the Agent model."""
    
    @pytest.mark.asyncio
    async def test_create_agent(self, test_db_session):
        """Test creating an agent."""
        user_id = uuid4()
        agent = Agent(
            name="Test Agent",
            description="Test description",
            config={"test": "config"},
            tags=["test", "agent"],
            status=AgentStatus.DRAFT,
            user_id=user_id
        )
        
        test_db_session.add(agent)
        await test_db_session.flush()
        
        # Verify the agent was created with a UUID
        assert isinstance(agent.id, UUID)
        assert agent.name == "Test Agent"
        assert agent.status == AgentStatus.DRAFT
        assert agent.user_id == user_id
        
    @pytest.mark.asyncio
    async def test_agent_with_versions(self, test_db_session):
        """Test creating an agent with versions."""
        user_id = uuid4()
        
        # Create agent
        agent = Agent(
            name="Agent with Versions",
            description="Test agent with versions",
            config={"test": "config"},
            status=AgentStatus.DRAFT,
            user_id=user_id
        )
        
        test_db_session.add(agent)
        await test_db_session.flush()
        
        # Create versions
        version1 = AgentVersion(
            agent_id=agent.id,
            user_id=user_id,
            version_number=1,
            config_snapshot={"version": 1, "test": "config"},
            change_summary="Initial version"
        )
        
        version2 = AgentVersion(
            agent_id=agent.id,
            user_id=user_id,
            version_number=2,
            config_snapshot={"version": 2, "test": "config"},
            change_summary="Updated version"
        )
        
        test_db_session.add_all([version1, version2])
        await test_db_session.flush()
        
        # Query the agent with versions
        result = await test_db_session.execute(
            select(Agent)
            .where(Agent.id == agent.id)
        )
        agent_with_versions = result.scalar_one()
        
        # Verify versions are available through relationship
        await test_db_session.refresh(agent_with_versions, ["versions"])
        assert len(agent_with_versions.versions) == 2
        
        # Verify they're ordered by version_number descending
        assert agent_with_versions.versions[0].version_number == 2
        assert agent_with_versions.versions[1].version_number == 1


class TestAgentVersionModel:
    """Test suite for the AgentVersion model."""
    
    @pytest.mark.asyncio
    async def test_create_agent_version(self, test_db_session):
        """Test creating an agent version."""
        user_id = uuid4()
        
        # Create agent first
        agent = Agent(
            name="Test Agent for Version",
            description="Test description",
            config={"test": "config"},
            status=AgentStatus.DRAFT,
            user_id=user_id
        )
        
        test_db_session.add(agent)
        await test_db_session.flush()
        
        # Create version
        version = AgentVersion(
            agent_id=agent.id,
            user_id=user_id,
            version_number=1,
            config_snapshot={"test": "config_snapshot"},
            change_summary="Test version"
        )
        
        test_db_session.add(version)
        await test_db_session.flush()
        
        # Verify the version was created with a UUID
        assert isinstance(version.id, UUID)
        assert version.agent_id == agent.id
        assert version.version_number == 1
        assert version.config_snapshot == {"test": "config_snapshot"}
