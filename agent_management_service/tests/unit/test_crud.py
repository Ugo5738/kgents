"""
Unit tests for CRUD operations.
"""
import pytest
from fastapi import HTTPException
from uuid import UUID, uuid4

from agent_management_service.crud import agents as agent_crud
from agent_management_service.crud import versions as version_crud
from agent_management_service.models.agent import AgentStatus
from agent_management_service.schemas.agent import AgentCreate, AgentUpdate
from agent_management_service.schemas.agent_version import AgentVersionCreate


class TestAgentCRUD:
    """Test suite for agent CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_agent(self, test_db_session):
        """Test creating an agent."""
        user_id = uuid4()
        agent_data = AgentCreate(
            name="Test Agent",
            description="Test description",
            config={"test": "config"},
            tags=["test", "agent"],
            status=AgentStatus.DRAFT
        )

        agent = await agent_crud.create_agent(test_db_session, agent_data, user_id)

        # Verify the agent was created
        assert agent.name == "Test Agent"
        assert agent.description == "Test description"
        assert agent.config == {"test": "config"}
        assert agent.tags == ["test", "agent"]
        assert agent.status == AgentStatus.DRAFT
        assert agent.user_id == user_id

        # Verify a version was created
        assert len(agent.versions) == 1
        assert agent.versions[0].version_number == 1

    @pytest.mark.asyncio
    async def test_get_agent(self, test_db_session):
        """Test getting an agent."""
        # Create an agent first
        user_id = uuid4()
        agent_data = AgentCreate(
            name="Agent to Get",
            description="Test description",
            config={"test": "config"},
            status=AgentStatus.DRAFT
        )
        created_agent = await agent_crud.create_agent(test_db_session, agent_data, user_id)
        
        # Get the agent
        agent = await agent_crud.get_agent(test_db_session, created_agent.id, user_id)
        
        # Verify the agent was retrieved
        assert agent.id == created_agent.id
        assert agent.name == "Agent to Get"
        
        # Test getting with wrong user ID
        wrong_user_id = uuid4()
        with pytest.raises(HTTPException) as excinfo:
            await agent_crud.get_agent(test_db_session, created_agent.id, wrong_user_id)
        assert excinfo.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_agents(self, test_db_session):
        """Test listing agents."""
        user_id = uuid4()
        
        # Create multiple agents
        for i in range(5):
            agent_data = AgentCreate(
                name=f"Test Agent {i}",
                description=f"Test description {i}",
                config={"test": f"config {i}"},
                status=AgentStatus.DRAFT
            )
            await agent_crud.create_agent(test_db_session, agent_data, user_id)
        
        # Get all agents
        agents, total = await agent_crud.get_agents(test_db_session, user_id)
        
        # Verify agents were retrieved
        assert total == 5
        assert len(agents) == 5
        
        # Test pagination
        agents, total = await agent_crud.get_agents(test_db_session, user_id, skip=2, limit=2)
        assert total == 5
        assert len(agents) == 2
        
        # Test filtering by status
        published_agent = AgentCreate(
            name="Published Agent",
            description="Published description",
            config={"test": "published"},
            status=AgentStatus.PUBLISHED
        )
        await agent_crud.create_agent(test_db_session, published_agent, user_id)
        
        agents, total = await agent_crud.get_agents(
            test_db_session, 
            user_id, 
            status=AgentStatus.PUBLISHED
        )
        assert total == 1
        assert agents[0].name == "Published Agent"

    @pytest.mark.asyncio
    async def test_update_agent(self, test_db_session):
        """Test updating an agent."""
        user_id = uuid4()
        
        # Create an agent
        agent_data = AgentCreate(
            name="Agent to Update",
            description="Original description",
            config={"original": "config"},
            status=AgentStatus.DRAFT
        )
        created_agent = await agent_crud.create_agent(test_db_session, agent_data, user_id)
        
        # Update the agent
        update_data = AgentUpdate(
            name="Updated Agent",
            description="Updated description",
            config={"updated": "config"}
        )
        updated_agent = await agent_crud.update_agent(
            test_db_session, 
            created_agent.id, 
            update_data, 
            user_id
        )
        
        # Verify the agent was updated
        assert updated_agent.name == "Updated Agent"
        assert updated_agent.description == "Updated description"
        assert updated_agent.config == {"updated": "config"}
        
        # Verify a new version was created
        await test_db_session.refresh(updated_agent, ["versions"])
        assert len(updated_agent.versions) == 2
        assert updated_agent.versions[0].version_number == 2
        
        # Test updating without creating a version
        update_data = AgentUpdate(name="No Version Update")
        updated_agent = await agent_crud.update_agent(
            test_db_session, 
            updated_agent.id, 
            update_data, 
            user_id,
            create_version=False
        )
        
        # Verify no new version was created
        await test_db_session.refresh(updated_agent, ["versions"])
        assert len(updated_agent.versions) == 2

    @pytest.mark.asyncio
    async def test_delete_agent(self, test_db_session):
        """Test deleting an agent."""
        user_id = uuid4()
        
        # Create an agent
        agent_data = AgentCreate(
            name="Agent to Delete",
            description="Test description",
            config={"test": "config"},
            status=AgentStatus.DRAFT
        )
        created_agent = await agent_crud.create_agent(test_db_session, agent_data, user_id)
        
        # Delete the agent
        result = await agent_crud.delete_agent(test_db_session, created_agent.id, user_id)
        assert result is True
        
        # Verify the agent was deleted
        with pytest.raises(HTTPException):
            await agent_crud.get_agent(test_db_session, created_agent.id, user_id)


class TestVersionCRUD:
    """Test suite for agent version CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_agent_version(self, test_db_session):
        """Test creating an agent version."""
        user_id = uuid4()
        
        # Create an agent first
        agent_data = AgentCreate(
            name="Agent for Versioning",
            description="Test description",
            config={"test": "config"},
            status=AgentStatus.DRAFT
        )
        agent = await agent_crud.create_agent(test_db_session, agent_data, user_id)
        
        # Create a new version
        version_data = AgentVersionCreate(
            agent_id=agent.id,
            config_snapshot={"updated": "config"},
            change_summary="Manual version creation"
        )
        
        version = await version_crud.create_agent_version(test_db_session, version_data, user_id)
        
        # Verify the version was created
        assert version.agent_id == agent.id
        assert version.version_number == 2  # Because create_agent already creates version 1
        assert version.config_snapshot == {"updated": "config"}
        assert version.change_summary == "Manual version creation"

    @pytest.mark.asyncio
    async def test_get_agent_versions(self, test_db_session):
        """Test getting agent versions."""
        user_id = uuid4()
        
        # Create an agent with multiple versions
        agent_data = AgentCreate(
            name="Agent with Multiple Versions",
            description="Test description",
            config={"test": "config"},
            status=AgentStatus.DRAFT
        )
        agent = await agent_crud.create_agent(test_db_session, agent_data, user_id)
        
        # Create additional versions
        for i in range(2, 5):
            version_data = AgentVersionCreate(
                agent_id=agent.id,
                config_snapshot={"version": i},
                change_summary=f"Version {i}"
            )
            await version_crud.create_agent_version(test_db_session, version_data, user_id)
        
        # Get all versions
        versions, total = await version_crud.get_agent_versions(test_db_session, agent.id, user_id)
        
        # Verify versions were retrieved
        assert total == 4  # 1 initial + 3 additional
        assert len(versions) == 4
        
        # Verify descending order
        assert versions[0].version_number == 4
        assert versions[1].version_number == 3
        assert versions[2].version_number == 2
        assert versions[3].version_number == 1

    @pytest.mark.asyncio
    async def test_get_latest_agent_version(self, test_db_session):
        """Test getting the latest agent version."""
        user_id = uuid4()
        
        # Create an agent with multiple versions
        agent_data = AgentCreate(
            name="Agent for Latest Version",
            description="Test description",
            config={"test": "config"},
            status=AgentStatus.DRAFT
        )
        agent = await agent_crud.create_agent(test_db_session, agent_data, user_id)
        
        # Create additional versions
        for i in range(2, 4):
            version_data = AgentVersionCreate(
                agent_id=agent.id,
                config_snapshot={"version": i},
                change_summary=f"Version {i}"
            )
            await version_crud.create_agent_version(test_db_session, version_data, user_id)
        
        # Get latest version
        latest = await version_crud.get_latest_agent_version(test_db_session, agent.id, user_id)
        
        # Verify latest version
        assert latest.version_number == 3
