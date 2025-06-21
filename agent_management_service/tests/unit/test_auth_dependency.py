"""
Tests for authentication dependencies.
"""
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from agent_management_service.dependencies.auth import get_current_user_id


@pytest.mark.asyncio
async def test_get_current_user_id_success():
    """Test successful extraction of user ID from request state."""
    # Arrange
    mock_request = AsyncMock()
    test_user_id = str(uuid.uuid4())
    mock_request.state.user_id = test_user_id
    
    # Act
    user_id = await get_current_user_id(mock_request)
    
    # Assert
    assert user_id == test_user_id


@pytest.mark.asyncio
async def test_get_current_user_id_missing():
    """Test handling of missing user ID in request state."""
    # Arrange
    mock_request = AsyncMock()
    mock_request.state.user_id = None
    
    # Act & Assert
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user_id(mock_request)
    
    assert excinfo.value.status_code == 401
    assert "Not authenticated" in str(excinfo.value.detail)


@pytest.mark.asyncio
async def test_get_current_user_id_no_state():
    """Test handling when state has no user_id attribute."""
    # Arrange
    mock_request = AsyncMock()
    # Delete the user_id attribute from state
    delattr(mock_request.state, "user_id")
    
    # Act & Assert
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user_id(mock_request)
    
    assert excinfo.value.status_code == 401
    assert "Not authenticated" in str(excinfo.value.detail)
