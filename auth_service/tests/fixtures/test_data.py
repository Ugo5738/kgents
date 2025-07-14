"""
Test data fixtures for tests.
Provides fixtures for creating and managing test data across test cases.
"""
import uuid
from typing import Dict, List, Optional, Tuple, Any, Callable

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from auth_service.models import Profile, Role, Permission, UserRole
from auth_service.crud.profiles import create_profile, update_profile, get_profile_by_user_id

# Import TestDataFactory to generate test data

from tests.helpers.test_data_factory import TestDataFactory


class TestDataManager:
    """
    Helper class to manage test data creation and cleanup.
    This makes it easier to create complex test data scenarios while maintaining
    proper relationships and foreign keys between entities.
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.created_profiles: List[Profile] = []
        self.created_roles: List[Role] = []
        self.created_permissions: List[Permission] = []
        self.created_user_roles: List[UserRole] = []
    
    async def create_profile(self, user_id: Optional[str] = None, **kwargs) -> Profile:
        """Create a profile and track it for potential cleanup"""
        user_id = user_id or str(uuid.uuid4())
        profile_data = TestDataFactory.create_profile_data(user_id=user_id, **kwargs)
        profile = await create_profile(self.db, profile_in=profile_data)
        self.created_profiles.append(profile)
        return profile
    
    async def create_role(self, **kwargs) -> Role:
        """Create a role and track it for potential cleanup"""
        role = TestDataFactory.create_role(**kwargs)
        self.db.add(role)
        await self.db.flush()
        await self.db.refresh(role)
        self.created_roles.append(role)
        return role
    
    async def create_permission(self, **kwargs) -> Permission:
        """Create a permission and track it for potential cleanup"""
        permission = TestDataFactory.create_permission(**kwargs)
        self.db.add(permission)
        await self.db.flush()
        await self.db.refresh(permission)
        self.created_permissions.append(permission)
        return permission
    
    async def create_user_role(self, 
                               user_id: Optional[str] = None, 
                               role_id: Optional[uuid.UUID] = None) -> UserRole:
        """Create a user-role association and track it for potential cleanup"""
        user_id = user_id or str(uuid.uuid4())
        
        # If role_id not provided, create a new role
        if not role_id:
            role = await self.create_role()
            role_id = role.id
        
        # Create user role using the factory and add directly to DB
        user_role = TestDataFactory.create_user_role(user_id=user_id, role_id=role_id)
        self.db.add(user_role)
        await self.db.flush()
        await self.db.refresh(user_role)
        
        self.created_user_roles.append(user_role)
        return user_role
    
    async def create_user_with_roles(self, 
                                    user_id: Optional[str] = None,
                                    roles_count: int = 1,
                                    role_names: Optional[List[str]] = None) -> Tuple[Profile, List[Role]]:
        """
        Create a complete user with profile and associated roles
        Returns the profile and list of roles created
        """
        user_id = user_id or str(uuid.uuid4())
        profile = await self.create_profile(user_id=user_id)
        
        roles = []
        # Create roles with specific names if provided, otherwise use default names
        if role_names:
            for role_name in role_names:
                role = await self.create_role(name=role_name)
                roles.append(role)
                await self.create_user_role(user_id=user_id, role_id=role.id)
        else:
            for _ in range(roles_count):
                role = await self.create_role()
                roles.append(role)
                await self.create_user_role(user_id=user_id, role_id=role.id)
                
        return profile, roles
        
    
    async def cleanup(self):
        """Clean up all created test data (if needed)"""
        # In most cases, the transaction rollback will handle this,
        # but we maintain the ability to explicitly clean up if needed
        pass


@pytest.fixture
async def test_data(db_session: AsyncSession) -> TestDataManager:
    """
    Fixture providing a test data manager for easy creation of test data.
    The test data manager tracks created objects and can clean them up if needed.
    All created data is automatically rolled back after the test via the db_session fixture.
    """
    manager = TestDataManager(db_session)
    try:
        yield manager
    finally:
        # Handle any explicit cleanup if needed
        await manager.cleanup()
