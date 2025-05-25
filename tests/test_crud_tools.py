import asyncio
import os
import sys

sys.path.insert(0, os.getcwd())

import pytest

from app.db import crud_tools
from app.models.tool import ToolCreate, ToolResponse, ToolUpdate


class DummyTable:
    def __init__(self, storage):
        self.storage = storage
        self.filter = None
        self.data = None
        self.pending_update = None
        self.pending_delete = False

    def insert(self, data):
        new_id = max(self.storage.keys(), default=0) + 1
        record = {"id": new_id, **data}
        self.storage[new_id] = record
        self.data = [record]
        return self

    def select(self, *_):
        return self

    def eq(self, key, val):
        self.filter = (key, val)
        # apply pending update if present
        if hasattr(self, "pending_update") and self.pending_update:
            record = self.storage.get(val)
            if record:
                record.update(self.pending_update)
        # handle pending delete
        if self.pending_delete:
            self.storage.pop(val, None)
            self.data = []
            return self
        # filter storage
        if key == "id":
            record = self.storage.get(val)
            self.data = [record] if record else []
        else:
            self.data = [r for r in self.storage.values() if r.get(key) == val]
        return self

    def update(self, update_data):
        # store update until filter is applied
        self.pending_update = update_data
        return self

    def delete(self):
        # mark for deletion, actual removal happens at eq
        self.pending_delete = True
        return self

    def execute(self):
        class Resp:
            def __init__(self, data):
                self.data = data

        return Resp(self.data)


class DummyClient:
    def __init__(self, storage):
        self.storage = storage

    def table(self, name):
        return DummyTable(self.storage)


@pytest.fixture(autouse=True)
def stub_supabase(monkeypatch):
    """Stub get_supabase_client to return DummyClient."""
    storage = {}

    async def dummy_get_supabase_client():
        return DummyClient(storage)

    monkeypatch.setattr(crud_tools, "get_supabase_client", dummy_get_supabase_client)
    return storage


def test_tool_crud_operations(stub_supabase):
    """Test create, get, list, update, delete for tools CRUD."""
    storage = stub_supabase
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Create tool
    create_data = ToolCreate(
        name="Tool1",
        description="A test tool",
        tool_type="typeA",
        definition={"key": "value"},
    )
    tool = loop.run_until_complete(crud_tools.create_tool(1, create_data))
    assert isinstance(tool, ToolResponse)
    assert tool.id == 1
    assert tool.user_id == 1
    assert storage[1]["name"] == "Tool1"

    # Get by ID
    fetched = loop.run_until_complete(crud_tools.get_tool_by_id(1))
    assert fetched == tool

    # List by user
    lst = loop.run_until_complete(crud_tools.get_all_tools_by_user(1))
    assert isinstance(lst, list)
    assert lst[0] == tool

    # Update tool
    update_data = ToolUpdate(name="Tool2")
    updated = loop.run_until_complete(crud_tools.update_tool(1, update_data))
    assert updated.name == "Tool2"
    assert storage[1]["name"] == "Tool2"

    # Delete tool
    loop.run_until_complete(crud_tools.delete_tool(1))
    assert storage == {}

    # Get after delete
    none_tool = loop.run_until_complete(crud_tools.get_tool_by_id(1))
    assert none_tool is None
