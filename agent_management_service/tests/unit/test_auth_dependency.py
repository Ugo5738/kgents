"""
Tests for authentication dependencies.
"""
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi import HTTPException, Depends

from agent_management_service.dependencies.auth import get_current_user_id, validate_token


@pytest.mark.asyncio
async def test_get_current_user_id_success():
    """Test successful extraction of user ID from request state."""
    # Arrange
    mock_request = AsyncMock()
    test_user_id = str(uuid.uuid4())
    
    # Set up the user dict as expected by the implementation
    mock_request.state.user = {"sub": test_user_id}
    
    # Mock the token_data dependency
    token_data = {"sub": test_user_id}
    
    # Act
    user_id = await get_current_user_id(mock_request, token_data)
    
    # Assert
    assert str(user_id) == test_user_id


@pytest.mark.asyncio
async def test_get_current_user_id_missing():
    """Test handling of missing user ID in request state."""
    # Arrange
    mock_request = AsyncMock()
    # Set user to None to simulate missing user
    mock_request.state.user = None
    
    # Mock token data
    token_data = {"sub": "some-id"}
    
    # Act & Assert
    with pytest.raises(RuntimeError) as excinfo:
        await get_current_user_id(mock_request, token_data)
    
    assert "User data not found in request state" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_current_user_id_no_state():
    """Test handling when state has no user attribute."""
    # Arrange
    mock_request = AsyncMock()
    # Delete the user attribute from state
    delattr(mock_request.state, "user")
    
    # Mock token data
    token_data = {"sub": "some-id"}
    
    # Act & Assert
    with pytest.raises(RuntimeError) as excinfo:
        await get_current_user_id(mock_request, token_data)
    
    assert "User data not found in request state" in str(excinfo.value)
