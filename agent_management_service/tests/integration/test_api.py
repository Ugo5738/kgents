"""
Integration tests for API endpoints.
"""
import json
import uuid
from typing import Dict, Any

import pytest
from fastapi import status
from sqlalchemy import select

from agent_management_service.models import Agent
from agent_management_service.models.agent import AgentStatus


@pytest.fixture
def agent_payload() -> Dict[str, Any]:
    """Return a test agent payload for API creation."""
    return {
        "name": "Test API Agent",
        "description": "Agent created through API testing",
        "config": {"test": "integration", "source": "api_test"},
        "tags": ["test", "api", "integration"],
        "status": "draft"
    }


@pytest.fixture
def update_payload() -> Dict[str, Any]:
    """Return a test agent update payload for API testing."""
    return {
        "name": "Updated API Agent",
        "description": "Agent updated through API testing",
        "tags": ["updated", "test"],
        "config": {"source": "updated_api_test", "test": "updated_config"}  # Add config change to trigger version creation
    }


@pytest.mark.asyncio
async def test_create_agent_endpoint(
    client, mock_validate_token, agent_payload, test_user_id, mock_token
):
    """Test creating an agent through the API."""
    # Make API call
    response = await client.post(
        "/api/v1/agents/",
        json=agent_payload,
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    
    # Verify response
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == agent_payload["name"]
    assert data["description"] == agent_payload["description"]
    assert data["config"] == agent_payload["config"]
    assert data["tags"] == agent_payload["tags"]
    assert data["user_id"] == test_user_id


@pytest.mark.asyncio
async def test_get_agents_endpoint(
    client, db_session, mock_validate_token, agent_payload, mock_token
):
    """Test listing agents through the API."""
    # Create multiple agents through the API
    for i in range(3):
        payload = agent_payload.copy()
        payload["name"] = f"Test API Agent {i}"
        await client.post(
            "/api/v1/agents/",
            json=payload,
            headers={"Authorization": f"Bearer {mock_token}"}
        )
    
    # Get agents through API
    response = await client.get(
        "/api/v1/agents/",
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    
    # Test pagination
    response = await client.get(
        "/api/v1/agents/?skip=1&limit=1",
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 1
    assert data["page"] == 2
    assert data["size"] == 1
    assert data["pages"] == 3
    assert data["has_next"] == True
    assert data["has_prev"] == True


@pytest.mark.asyncio
async def test_get_single_agent_endpoint(
    client, db_session, mock_validate_token, agent_payload, mock_token
):
    """Test getting a single agent through the API."""
    # Create an agent
    response = await client.post(
        "/api/v1/agents/",
        json=agent_payload,
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    created = response.json()
    agent_id = created["id"]
    
    # Get the agent through API
    response = await client.get(
        f"/api/v1/agents/{agent_id}",
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == agent_id
    assert data["name"] == agent_payload["name"]
    
    # Test getting agent with versions
    response = await client.get(
        f"/api/v1/agents/{agent_id}/with-versions",
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    
    # Verify response includes versions
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "versions" in data
    assert len(data["versions"]) == 1  # Initial version


@pytest.mark.asyncio
async def test_update_agent_endpoint(
    client, db_session, mock_validate_token, agent_payload, update_payload, mock_token
):
    """Test updating an agent through the API."""
    # Create an agent
    response = await client.post(
        "/api/v1/agents/",
        json=agent_payload,
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    created = response.json()
    agent_id = created["id"]
    
    # Update the agent through API
    response = await client.patch(
        f"/api/v1/agents/{agent_id}",
        json=update_payload,
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == update_payload["name"]
    assert data["description"] == update_payload["description"]
    assert data["tags"] == update_payload["tags"]
    
    # Verify a new version was created
    response = await client.get(
        f"/api/v1/agents/{agent_id}/with-versions",
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    data = response.json()
    assert len(data["versions"]) == 2


@pytest.mark.asyncio
async def test_agent_lifecycle_endpoints(
    client, db_session, mock_validate_token, agent_payload, mock_token
):
    """Test agent lifecycle operations (publish/archive) through the API."""
    # Create a draft agent
    response = await client.post(
        "/api/v1/agents/",
        json=agent_payload,
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    created = response.json()
    agent_id = created["id"]
    
    # Publish the agent
    response = await client.post(
        f"/api/v1/agents/{agent_id}/publish",
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "published"
    assert data["active_version_id"] is not None
    
    # Archive the agent
    response = await client.post(
        f"/api/v1/agents/{agent_id}/archive",
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "archived"


@pytest.mark.asyncio
async def test_delete_agent_endpoint(
    client, db_session, mock_validate_token, agent_payload, mock_token
):
    """Test deleting an agent through the API."""
    # Create an agent
    response = await client.post(
        "/api/v1/agents/",
        json=agent_payload,
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    created = response.json()
    agent_id = created["id"]
    
    # Delete the agent through API
    response = await client.delete(
        f"/api/v1/agents/{agent_id}",
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert "deleted successfully" in data["message"]
    
    # Verify the agent is deleted
    response = await client.get(
        f"/api/v1/agents/{agent_id}",
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_agent_versions_endpoints(
    client, db_session, mock_validate_token, agent_payload, mock_token
):
    """Test agent version API operations."""
    # Create an agent
    response = await client.post(
        "/api/v1/agents/",
        json=agent_payload,
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    created = response.json()
    agent_id = created["id"]
    
    # Create a new version manually
    version_payload = {
        "agent_id": agent_id,  # Add agent_id to the payload as required by API
        "config_snapshot": {"updated": "config", "version": 2},
        "change_summary": "Manual API version creation"
    }
    
    response = await client.post(
        f"/api/v1/agents/{agent_id}/versions/",
        json=version_payload,
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    
    # Print response for debugging
    print(f"\nVersion creation response: {response.status_code}")
    print(f"Response body: {response.json()}")

    # Verify response
    assert response.status_code == status.HTTP_201_CREATED
    version_data = response.json()
    assert version_data["version_number"] == 2
    assert version_data["change_summary"] == "Manual API version creation"
    
    # List versions
    response = await client.get(
        f"/api/v1/agents/{agent_id}/versions/",
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    
    # Get latest version
    response = await client.get(
        f"/api/v1/agents/{agent_id}/versions/latest",
        headers={"Authorization": f"Bearer {mock_token}"}
    )
    
    # Verify response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["version_number"] == 2
