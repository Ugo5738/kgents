import os
import sys

sys.path.insert(0, os.getcwd())

import pytest
from fastapi.testclient import TestClient

from app.db import crud_tools
from app.models.tool import ToolCreate, ToolResponse, ToolUpdate
from main import app


@pytest.fixture(autouse=True)
def dummy_tool_crud(monkeypatch):
    """Stub tool CRUD functions for testing without Supabase."""
    storage: dict[int, ToolResponse] = {}

    async def dummy_create_tool(user_id: int, tool_create: ToolCreate) -> ToolResponse:
        tool = ToolResponse(
            id=1,
            user_id=user_id,
            name=tool_create.name,
            description=tool_create.description,
            tool_type=tool_create.tool_type,
            definition=tool_create.definition,
        )
        storage[1] = tool
        return tool

    async def dummy_get_tool_by_id(tool_id: int) -> ToolResponse | None:
        return storage.get(tool_id)

    async def dummy_get_all_tools_by_user(user_id: int) -> list[ToolResponse]:
        return [t for t in storage.values() if t.user_id == user_id]

    async def dummy_update_tool(
        tool_id: int, tool_update: ToolUpdate
    ) -> ToolResponse | None:
        existing = storage.get(tool_id)
        if not existing:
            return None
        updated = existing.copy(update=tool_update.dict(exclude_unset=True))
        storage[tool_id] = updated
        return updated

    async def dummy_delete_tool(tool_id: int) -> None:
        storage.pop(tool_id, None)

    import app.api.v1.tools.routes as tools_module

    monkeypatch.setattr(tools_module, "crud_create_tool", dummy_create_tool)
    monkeypatch.setattr(tools_module, "crud_get_tool_by_id", dummy_get_tool_by_id)
    monkeypatch.setattr(tools_module, "crud_get_all_tools", dummy_get_all_tools_by_user)
    monkeypatch.setattr(tools_module, "crud_update_tool", dummy_update_tool)
    monkeypatch.setattr(tools_module, "crud_delete_tool", dummy_delete_tool)

    # Override get_current_user_id dependency to always return user_id=1
    from app.api.v1.tools.routes import get_current_user_id

    app.dependency_overrides[get_current_user_id] = lambda: 1


def test_tool_crud_flow():
    """Test creating, listing, retrieving, updating, and deleting a tool."""
    with TestClient(app) as client:
        # Create tool
        create_payload = {
            "name": "TestTool",
            "description": "A test tool for API testing",
            "tool_type": "openapi",
            "definition": {
                "openapi": "3.0.0",
                "info": {"title": "Test API", "version": "1.0.0"},
                "paths": {"/test": {"get": {"summary": "Test endpoint"}}},
            },
        }
        resp = client.post("/tools/", json=create_payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == 1
        assert data["user_id"] == 1
        assert data["name"] == "TestTool"
        assert data["tool_type"] == "openapi"

        # List tools
        resp = client.get("/tools/")
        assert resp.status_code == 200
        list_data = resp.json()
        assert isinstance(list_data, list)
        assert list_data[0] == data

        # Get by ID
        resp = client.get("/tools/1")
        assert resp.status_code == 200
        assert resp.json() == data

        # Update tool
        update_payload = {"name": "UpdatedTool", "description": "An updated test tool"}
        resp = client.put("/tools/1", json=update_payload)
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["name"] == "UpdatedTool"
        assert updated["description"] == "An updated test tool"
        assert updated["tool_type"] == "openapi"  # unchanged

        # Delete tool
        resp = client.delete("/tools/1")
        assert resp.status_code == 204

        # Ensure deletion
        resp = client.get("/tools/1")
        assert resp.status_code == 404


def test_tool_authorization():
    """Test that users can only access their own tools."""
    with TestClient(app) as client:
        # Create tool as user 1
        create_payload = {
            "name": "UserOneTool",
            "description": "Tool owned by user 1",
            "tool_type": "python_code",
            "definition": {"code": "print('Hello from user 1')"},
        }
        resp = client.post("/tools/", json=create_payload)
        assert resp.status_code == 201
        tool_data = resp.json()

        # Now simulate different user trying to access the tool
        # Override dependency to return user_id=2
        from app.api.v1.tools.routes import get_current_user_id

        app.dependency_overrides[get_current_user_id] = lambda: 2

        # Try to get tool as user 2 - should be forbidden
        resp = client.get("/tools/1")
        assert resp.status_code == 403
        assert "Not authorized" in resp.json()["detail"]

        # Try to update tool as user 2 - should be forbidden
        resp = client.put("/tools/1", json={"name": "HackedTool"})
        assert resp.status_code == 404  # Tool not found for this user

        # Try to delete tool as user 2 - should be forbidden
        resp = client.delete("/tools/1")
        assert resp.status_code == 404  # Tool not found for this user


def test_tool_not_found():
    """Test handling of non-existent tools."""
    with TestClient(app) as client:
        # Get non-existent tool
        resp = client.get("/tools/999")
        assert resp.status_code == 404
        assert "Tool not found" in resp.json()["detail"]

        # Update non-existent tool
        resp = client.put("/tools/999", json={"name": "NonExistent"})
        assert resp.status_code == 404

        # Delete non-existent tool
        resp = client.delete("/tools/999")
        assert resp.status_code == 404


def test_tool_health_check():
    """Test the health check endpoint."""
    with TestClient(app) as client:
        resp = client.get("/tools/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "tools healthy"}
