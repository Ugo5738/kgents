"""
Integration tests for tool category routes.

Tests the API endpoints for creating, reading, updating, and deleting tool categories.
"""

import uuid
import pytest
from fastapi import status

from tool_registry_service.dependencies import auth as auth_deps
from tool_registry_service.main import app


# Set up test authentication overrides
@pytest.fixture(autouse=True)
def override_auth_dependencies():
    """Override auth dependencies for testing."""
    app.dependency_overrides[auth_deps.get_current_user_id] = lambda: uuid.UUID("00000000-0000-0000-0000-000000000001")
    app.dependency_overrides[auth_deps.check_admin_role] = lambda: True
    yield
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_create_category(client, db_session):
    """Test creating a category via API."""
    # Define test data
    category_data = {
        "name": "Test API Category",
        "description": "Created through API test",
        "display_order": 1,
        "icon": "test-icon",
        "color": "#336699"
    }
    
    # Send request
    response = await client.post("/api/v1/categories/", json=category_data)
    
    # Check response
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == category_data["name"]
    assert data["description"] == category_data["description"]
    assert "id" in data
    
    # Verify ID is a valid UUID
    category_id = uuid.UUID(data["id"])
    assert isinstance(category_id, uuid.UUID)


@pytest.mark.asyncio
async def test_get_category(client, db_session, seed_test_data):
    """Test retrieving a category by ID."""
    # Get a category ID from test data
    category_id = seed_test_data["categories"][0].id
    
    # Send request
    response = await client.get(f"/api/v1/categories/{category_id}")
    
    # Check response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(category_id)
    assert data["name"] == seed_test_data["categories"][0].name


@pytest.mark.asyncio
async def test_get_category_not_found(client):
    """Test getting a non-existent category returns 404."""
    # Generate a random UUID
    random_id = uuid.uuid4()
    
    # Send request
    response = await client.get(f"/api/v1/categories/{random_id}")
    
    # Check response
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_categories(client, seed_test_data):
    """Test listing categories with pagination."""
    # Send request
    response = await client.get("/api/v1/categories/?page=1&page_size=10")
    
    # Check response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == len(seed_test_data["categories"])
    assert len(data["items"]) == len(seed_test_data["categories"])
    
    # Verify sorting by display_order
    for i, item in enumerate(data["items"]):
        assert item["name"] == seed_test_data["categories"][i].name


@pytest.mark.asyncio
async def test_list_categories_with_filter(client, seed_test_data):
    """Test listing categories with name filter."""
    # Find a category that has "API" in the name
    api_category = next((c for c in seed_test_data["categories"] if "API" in c.name), None)
    assert api_category is not None
    
    # Send request with filter
    response = await client.get(f"/api/v1/categories/?name=API")
    
    # Check response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] >= 1
    assert any(item["id"] == str(api_category.id) for item in data["items"])


@pytest.mark.asyncio
async def test_update_category(client, seed_test_data):
    """Test updating a category via API."""
    # Get a category ID from test data
    category_id = seed_test_data["categories"][0].id
    
    # Define update data
    update_data = {
        "name": "Updated Category Name",
        "description": "Updated through API test"
    }
    
    # Send request
    response = await client.patch(f"/api/v1/categories/{category_id}", json=update_data)
    
    # Check response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(category_id)
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]


@pytest.mark.asyncio
async def test_delete_category(client, seed_test_data):
    """Test deleting a category via API."""
    # Get a category ID from test data
    category_id = seed_test_data["categories"][2].id
    
    # Send delete request
    response = await client.delete(f"/api/v1/categories/{category_id}")
    
    # Check response
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Verify category is deleted by trying to get it
    get_response = await client.get(f"/api/v1/categories/{category_id}")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_category_non_admin_fails(client):
    """Test non-admin users cannot create categories."""
    # Override admin check to return False
    app.dependency_overrides[auth_deps.check_admin_role] = lambda: False
    
    # Define test data
    category_data = {"name": "Test Category"}
    
    # Send request
    response = await client.post("/api/v1/categories/", json=category_data)
    
    # Check that access is denied
    assert response.status_code == status.HTTP_403_FORBIDDEN
    
    # Restore admin check override
    app.dependency_overrides[auth_deps.check_admin_role] = lambda: True
