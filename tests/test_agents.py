import os
import sys

sys.path.insert(0, os.getcwd())

import pytest
from fastapi.testclient import TestClient

from app.db import crud_agents
from app.models.agent import AgentCreate, AgentResponse, AgentUpdate
from main import app


@pytest.fixture(autouse=True)
def dummy_agent_crud(monkeypatch):
    """Stub agent CRUD functions for testing without Supabase."""
    storage: dict[int, AgentResponse] = {}

    async def dummy_create_agent(
        user_id: int, agent_create: AgentCreate
    ) -> AgentResponse:
        agent = AgentResponse(
            id=1,
            user_id=user_id,
            name=agent_create.name,
            description=agent_create.description,
            langflow_flow_json=agent_create.langflow_flow_json,
        )
        storage[1] = agent
        return agent

    async def dummy_get_agent_by_id(agent_id: int) -> AgentResponse | None:
        return storage.get(agent_id)

    async def dummy_get_all_agents_by_user(user_id: int) -> list[AgentResponse]:
        return [a for a in storage.values() if a.user_id == user_id]

    async def dummy_update_agent(
        agent_id: int, agent_update: AgentUpdate
    ) -> AgentResponse | None:
        existing = storage.get(agent_id)
        if not existing:
            return None
        updated = existing.model_copy(
            update=agent_update.model_dump(exclude_unset=True)
        )
        storage[agent_id] = updated
        return updated

    async def dummy_delete_agent(agent_id: int) -> None:
        storage.pop(agent_id, None)

    import app.api.v1.agents.routes as agents_module

    monkeypatch.setattr(agents_module, "crud_create_agent", dummy_create_agent)
    monkeypatch.setattr(agents_module, "crud_get_agent_by_id", dummy_get_agent_by_id)
    monkeypatch.setattr(
        agents_module, "crud_get_all_agents", dummy_get_all_agents_by_user
    )
    monkeypatch.setattr(agents_module, "crud_update_agent", dummy_update_agent)
    monkeypatch.setattr(agents_module, "crud_delete_agent", dummy_delete_agent)

    # Override get_current_user_id dependency to always return user_id=1
    from app.api.v1.agents.routes import get_current_user_id

    app.dependency_overrides[get_current_user_id] = lambda: 1


def test_agent_crud_flow():
    """Test creating, listing, retrieving, updating, and deleting an agent."""
    with TestClient(app) as client:
        # Create agent
        create_payload = {
            "name": "TestAgent",
            "description": "A test agent",
            "langflow_flow_json": {"nodes": []},
        }
        resp = client.post("/agents/", json=create_payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == 1
        assert data["user_id"] == 1
        assert data["name"] == "TestAgent"

        # List agents
        resp = client.get("/agents/")
        assert resp.status_code == 200
        list_data = resp.json()
        assert isinstance(list_data, list)
        assert list_data[0] == data

        # Get by ID
        resp = client.get("/agents/1")
        assert resp.status_code == 200
        assert resp.json() == data

        # Update agent
        update_payload = {"name": "UpdatedAgent"}
        resp = client.put("/agents/1", json=update_payload)
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["name"] == "UpdatedAgent"

        # Delete agent
        resp = client.delete("/agents/1")
        assert resp.status_code == 204

        # Ensure deletion
        resp = client.get("/agents/1")
        assert resp.status_code == 404
