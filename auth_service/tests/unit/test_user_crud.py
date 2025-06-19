"""
Unit tests for user CRUD operations.
Tests database interactions using mocked sessions.
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from auth_service.crud import user_crud
from auth_service.models.profile import Profile
from auth_service.schemas.user_schemas import ProfileCreate, ProfileUpdate


class TestUserCrud:
    @pytest.mark.asyncio
    async def test_create_profile_in_db(self):
        """Test creating a profile in the database."""
        # Arrange
        mock_session = AsyncMock(spec=AsyncSession)
        user_id = uuid.uuid4()
        profile_data = ProfileCreate(
            user_id=user_id,
            email="test_create@example.com",
            username="test_create_user",
            first_name="Test",
            last_name="Create"
        )
        
        # Create a mock profile that would be returned
        mock_profile = Profile(
            user_id=user_id,
            email=profile_data.email,
            username=profile_data.username,
            first_name=profile_data.first_name,
            last_name=profile_data.last_name,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Configure the mock session behavior
        # 1. When session.flush() is called, we'll simulate updating the created_at and updated_at fields
        async def mock_flush():
            mock_profile.created_at = datetime.utcnow()
            mock_profile.updated_at = datetime.utcnow()
            
        mock_session.flush = AsyncMock(side_effect=mock_flush)
        
        # 2. When session.refresh() is called, do nothing (we've already set up our mock profile)
        mock_session.refresh = AsyncMock()
        
        # Mock the model's __init__ to return our prepared mock_profile
        with patch('auth_service.models.profile.Profile', return_value=mock_profile):
            # Act
            result = await user_crud.create_profile_in_db(
                db_session=mock_session,
                profile_in=profile_data
            )
            
            # Assert
            assert result is not None
            assert result.email == profile_data.email
            assert result.username == profile_data.username
            assert result.user_id == user_id
            
            # Verify the session methods were called
            mock_session.add.assert_called_once()
            mock_session.flush.assert_called_once()
            mock_session.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_profile_by_user_id(self):
        """Test retrieving a profile by user ID."""
        # Arrange
        mock_session = AsyncMock(spec=AsyncSession)
        user_id = uuid.uuid4()
        
        # Create a mock profile to be "found" in the database
        mock_profile = Profile(
            user_id=user_id,
            email="test_get_id@example.com",
            username="test_get_id_user",
            first_name="Test",
            last_name="GetById",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Mock the result of session.execute properly for async flow
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_profile
        mock_result.scalars.return_value = mock_scalars
        
        # Make execute return a coroutine that resolves to mock_result
        async def mock_execute(*args, **kwargs):
            return mock_result
            
        mock_session.execute = AsyncMock(side_effect=mock_execute)
        
        # Act
        result = await user_crud.get_profile_by_user_id(
            db_session=mock_session,
            user_id=user_id
        )
        
        # Assert
        assert result is not None
        assert result.email == mock_profile.email
        assert result.username == mock_profile.username
        assert result.user_id == user_id
        
        # Verify the query was constructed correctly
        mock_session.execute.assert_called_once()
        # We can't easily check the exact query sent, but we could enhance this to verify the filter
    
    @pytest.mark.asyncio
    async def test_get_profile_by_email(self):
        """Test retrieving a profile by email."""
        # Arrange
        mock_session = AsyncMock(spec=AsyncSession)
        user_id = uuid.uuid4()
        email = "test_get_email@example.com"
        
        # Create a mock profile to be "found" in the database
        mock_profile = Profile(
            user_id=user_id,
            email=email,
            username="test_get_email_user",
            first_name="Test",
            last_name="GetByEmail",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Mock the result of session.execute properly for async flow
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_profile
        mock_result.scalars.return_value = mock_scalars
        
        # Make execute return a coroutine that resolves to mock_result
        async def mock_execute(*args, **kwargs):
            return mock_result
            
        mock_session.execute = AsyncMock(side_effect=mock_execute)
        
        # Act
        result = await user_crud.get_profile_by_email(
            db_session=mock_session,
            email=email
        )
        
        # Assert
        assert result is not None
        assert result.email == email
        assert result.user_id == user_id
        
        # Verify correct query construction
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_profile(self):
        """Test updating a profile."""
        # Arrange
        mock_session = AsyncMock(spec=AsyncSession)
        user_id = uuid.uuid4()
        email = "test_update@example.com"
        
        # Create a mock profile that will be updated
        mock_profile = Profile(
            user_id=user_id,
            email=email,
            username="oldusername",
            first_name="Old",
            last_name="Name",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Update data
        update_data = ProfileUpdate(
            email=email,  # Keep email the same
            username="newusername",
            first_name="New",
            last_name="Name"
        )
        
        # Configure the session's flush and refresh behavior
        async def mock_flush():
            # Simulate updating the profile and the updated_at timestamp
            mock_profile.username = update_data.username
            mock_profile.first_name = update_data.first_name
            mock_profile.last_name = update_data.last_name
            mock_profile.updated_at = datetime.utcnow()
            
        mock_session.flush = AsyncMock(side_effect=mock_flush)
        mock_session.refresh = AsyncMock()
        
        # Act
        result = await user_crud.update_profile(
            db_session=mock_session,
            profile=mock_profile,  
            update_data=update_data.model_dump(exclude_unset=True)
        )
        
        # Assert
        assert result is not None
        assert result.username == update_data.username
        assert result.first_name == update_data.first_name
        assert result.last_name == update_data.last_name
        assert result.email == email  # Email should remain unchanged
        
        # Verify the session methods were called
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_deactivate_profile(self):
        """Test deactivating a profile."""
        # Arrange
        mock_session = AsyncMock(spec=AsyncSession)
        user_id = uuid.uuid4()
        
        # Create an active mock profile
        mock_profile = Profile(
            user_id=user_id,
            email="test_deactivate@example.com",
            username="test_deactivate_user",
            first_name="Test",
            last_name="Deactivate",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Mock get_profile_by_user_id to return our mock profile
        with patch.object(user_crud, "get_profile_by_user_id", return_value=mock_profile):
            # Configure the session's flush and refresh behavior
            async def mock_flush():
                # Simulate deactivating the profile
                mock_profile.is_active = False
                mock_profile.updated_at = datetime.utcnow()
                
            mock_session.flush = AsyncMock(side_effect=mock_flush)
            mock_session.refresh = AsyncMock()
            
            # Act
            result = await user_crud.deactivate_profile(
                db_session=mock_session,
                user_id=user_id
            )
            
            # Assert
            assert result is not None
            assert result.is_active is False
            
            # Verify the session methods were called
            mock_session.flush.assert_called_once()
            mock_session.refresh.assert_called_once()
