"""
Unit tests for tool category CRUD operations.

Tests the database operations for creating, reading, updating, and deleting tool categories.
"""

import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import select

from tool_registry_service.crud.tool_categories import (
    create_tool_category,
    get_tool_category,
    list_tool_categories,
    update_tool_category,
    delete_tool_category,
)
from tool_registry_service.models.tool import ToolCategory
from tool_registry_service.schemas.tool import ToolCategoryCreate, ToolCategoryUpdate


@pytest.mark.asyncio
async def test_create_tool_category(db_session):
    """Test creating a tool category."""
    # Create category data
    category_data = ToolCategoryCreate(
        name="Test Category",
        description="Test description",
        display_order=1,
        icon="test-icon",
        color="#FF0000",
    )
    
    # Create category
    category = await create_tool_category(db_session, category_data)
    
    # Verify category was created with correct data
    assert category.id is not None
    assert category.name == "Test Category"
    assert category.description == "Test description"
    assert category.display_order == 1
    assert category.icon == "test-icon"
    assert category.color == "#FF0000"
    
    # Verify category exists in database
    result = await db_session.execute(
        select(ToolCategory).where(ToolCategory.id == category.id)
    )
    db_category = result.scalar_one_or_none()
    assert db_category is not None
    assert db_category.name == category_data.name


@pytest.mark.asyncio
async def test_create_tool_category_duplicate_name(db_session):
    """Test creating a category with a duplicate name fails."""
    # Create initial category
    category_data = ToolCategoryCreate(name="Test Category")
    await create_tool_category(db_session, category_data)
    
    # Try to create another category with the same name
    duplicate_data = ToolCategoryCreate(name="Test Category")
    
    # Assert that HTTPException is raised
    with pytest.raises(HTTPException) as excinfo:
        await create_tool_category(db_session, duplicate_data)
    
    assert excinfo.value.status_code == 409
    assert "already exists" in excinfo.value.detail


@pytest.mark.asyncio
async def test_get_tool_category(db_session):
    """Test getting a tool category by ID."""
    # Create a category
    category_data = ToolCategoryCreate(name="Test Category")
    created = await create_tool_category(db_session, category_data)
    
    # Get the category
    category = await get_tool_category(db_session, created.id)
    
    # Verify correct category was retrieved
    assert category.id == created.id
    assert category.name == "Test Category"


@pytest.mark.asyncio
async def test_get_tool_category_not_found(db_session):
    """Test getting a non-existent category raises 404."""
    # Generate a random UUID
    random_id = uuid.uuid4()
    
    # Try to get a non-existent category
    with pytest.raises(HTTPException) as excinfo:
        await get_tool_category(db_session, random_id)
    
    assert excinfo.value.status_code == 404
    assert "not found" in excinfo.value.detail


@pytest.mark.asyncio
async def test_list_tool_categories(db_session):
    """Test listing tool categories with pagination."""
    # Create multiple categories
    for i in range(5):
        await create_tool_category(
            db_session, 
            ToolCategoryCreate(
                name=f"Category {i}", 
                display_order=i
            )
        )
    
    # List categories (first page)
    categories, count = await list_tool_categories(db_session, page=1, page_size=3)
    
    # Verify pagination works
    assert len(categories) == 3
    assert count == 5
    
    # Verify ordering by display_order
    assert categories[0].name == "Category 0"
    assert categories[1].name == "Category 1"
    assert categories[2].name == "Category 2"
    
    # Get second page
    categories_page2, _ = await list_tool_categories(db_session, page=2, page_size=3)
    
    # Verify second page has remaining categories
    assert len(categories_page2) == 2
    assert categories_page2[0].name == "Category 3"
    assert categories_page2[1].name == "Category 4"


@pytest.mark.asyncio
async def test_list_tool_categories_with_filter(db_session):
    """Test listing tool categories with name filter."""
    # Create categories with different names
    await create_tool_category(db_session, ToolCategoryCreate(name="API Tools"))
    await create_tool_category(db_session, ToolCategoryCreate(name="ML Tools"))
    await create_tool_category(db_session, ToolCategoryCreate(name="Utility Tools"))
    
    # Filter by name
    categories, count = await list_tool_categories(
        db_session, page=1, page_size=10, name_filter="API"
    )
    
    # Verify filter works
    assert len(categories) == 1
    assert count == 1
    assert categories[0].name == "API Tools"


@pytest.mark.asyncio
async def test_update_tool_category(db_session):
    """Test updating a tool category."""
    # Create a category
    category_data = ToolCategoryCreate(name="Original Name")
    category = await create_tool_category(db_session, category_data)
    
    # Update the category
    update_data = ToolCategoryUpdate(
        name="Updated Name", 
        description="Updated description"
    )
    updated = await update_tool_category(db_session, category.id, update_data)
    
    # Verify category was updated
    assert updated.id == category.id
    assert updated.name == "Updated Name"
    assert updated.description == "Updated description"
    
    # Verify update persisted in database
    result = await db_session.execute(
        select(ToolCategory).where(ToolCategory.id == category.id)
    )
    db_category = result.scalar_one()
    assert db_category.name == "Updated Name"
    assert db_category.description == "Updated description"


@pytest.mark.asyncio
async def test_update_tool_category_duplicate_name(db_session):
    """Test updating a category with a duplicate name fails."""
    # Create two categories
    await create_tool_category(db_session, ToolCategoryCreate(name="Category 1"))
    category2 = await create_tool_category(db_session, ToolCategoryCreate(name="Category 2"))
    
    # Try to update category2 to have the same name as category1
    update_data = ToolCategoryUpdate(name="Category 1")
    
    # Assert that HTTPException is raised
    with pytest.raises(HTTPException) as excinfo:
        await update_tool_category(db_session, category2.id, update_data)
    
    assert excinfo.value.status_code == 409
    assert "already exists" in excinfo.value.detail


@pytest.mark.asyncio
async def test_delete_tool_category(db_session):
    """Test deleting a tool category."""
    # Create a category
    category = await create_tool_category(db_session, ToolCategoryCreate(name="To Delete"))
    
    # Delete the category
    await delete_tool_category(db_session, category.id)
    
    # Verify category no longer exists
    result = await db_session.execute(
        select(ToolCategory).where(ToolCategory.id == category.id)
    )
    assert result.scalar_one_or_none() is None
