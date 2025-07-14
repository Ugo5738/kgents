"""
Test Data Factory for Auth Service Tests.

This module provides factory functions for generating consistent test data.
It helps maintain test isolation while providing realistic test data.
"""

import uuid
from datetime import datetime
from typing import Dict, Optional, Union

from auth_service.models.profile import Profile
from auth_service.models.role import Role
from auth_service.models.permission import Permission
from auth_service.models.user_role import UserRole
from auth_service.schemas.user_schemas import ProfileCreate, ProfileUpdate


class TestDataFactory:
    """Factory for generating test data with consistent and unique values."""

    @staticmethod
    def generate_unique_id(prefix: str = "") -> str:
        """
        Generate a unique ID for test data.
        
        Args:
            prefix: Optional prefix to add to the ID
            
        Returns:
            A string containing a timestamp and random UUID fragment
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_part = uuid.uuid4().hex[:8]
        if prefix:
            return f"{prefix}_{timestamp}_{unique_part}"
        return f"{timestamp}_{unique_part}"

    @staticmethod
    def create_test_user_id() -> str:
        """Create a consistent test user UUID string."""
        return str(uuid.uuid4())

    @staticmethod
    def create_profile_data(
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        username: Optional[str] = None,
        first_name: str = "Test",
        last_name: str = "User",
    ) -> ProfileCreate:
        """
        Create ProfileCreate object with test data.
        
        Args:
            user_id: Optional user ID (UUID string)
            email: Optional email address
            username: Optional username
            first_name: First name for the profile
            last_name: Last name for the profile
            
        Returns:
            ProfileCreate object with generated test data
        """
        test_id = TestDataFactory.generate_unique_id()
        
        if user_id is None:
            user_id = TestDataFactory.create_test_user_id()
            
        if email is None:
            email = f"test.user.{test_id}@example.com"
            
        if username is None:
            username = f"testuser_{test_id}"
            
        return ProfileCreate(
            user_id=user_id,
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )

    @staticmethod
    def create_profile_update_data(
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> ProfileUpdate:
        """
        Create ProfileUpdate object with test data.
        
        Args:
            email: Optional updated email
            first_name: Optional updated first name
            last_name: Optional updated last name
            
        Returns:
            ProfileUpdate object with provided or generated test data
        """
        test_id = TestDataFactory.generate_unique_id()
        
        update_data = {}
        if email is not None:
            update_data["email"] = email
        else:
            update_data["email"] = f"updated.{test_id}@example.com"
            
        if first_name is not None:
            update_data["first_name"] = first_name
        else:
            update_data["first_name"] = f"Updated{test_id}"
            
        if last_name is not None:
            update_data["last_name"] = last_name
        else:
            update_data["last_name"] = f"User{test_id}"
            
        return ProfileUpdate(**update_data)

    @staticmethod
    def create_auth_user_data(
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        username: Optional[str] = None,
    ) -> Dict[str, Union[str, Dict]]:
        """
        Create mock Supabase auth user data.
        
        Args:
            user_id: Optional user ID (UUID string)
            email: Optional email address
            username: Optional username
            
        Returns:
            Dictionary with mock Supabase auth user data
        """
        test_id = TestDataFactory.generate_unique_id()
        
        if user_id is None:
            user_id = TestDataFactory.create_test_user_id()
            
        if email is None:
            email = f"auth.user.{test_id}@example.com"
            
        if username is None:
            username = f"authuser_{test_id}"
            
        return {
            "id": user_id,
            "email": email,
            "app_metadata": {},
            "user_metadata": {"username": username},
            "phone": "",
            "phone_confirmed_at": None,
            "email_confirmed_at": datetime.now().isoformat(),
            "confirmed_at": datetime.now().isoformat(),
            "last_sign_in_at": datetime.now().isoformat(),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "identities": [],
            "aud": "authenticated",
            "role": "authenticated",
        }

    @staticmethod
    def create_role(
        name: Optional[str] = None, 
        description: Optional[str] = None
    ) -> Role:
        """
        Create a role object for testing.
        
        Args:
            name: Role name
            description: Role description
            
        Returns:
            Role model instance
        """
        if name is None:
            unique_id = TestDataFactory.generate_unique_id("role")
            name = f"test_role_{unique_id}"
            
        if description is None:
            description = f"Test role for {name}"
            
        role = Role(
            id=uuid.uuid4(),
            name=name,
            description=description,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        return role
    
    @staticmethod
    def create_permission(
        name: Optional[str] = None, 
        description: Optional[str] = None
    ) -> Permission:
        """
        Create a permission object for testing.
        
        Args:
            name: Permission name
            description: Permission description
            
        Returns:
            Permission model instance
        """
        if name is None:
            unique_id = TestDataFactory.generate_unique_id("perm")
            name = f"test:permission:{unique_id}"
            
        if description is None:
            description = f"Test permission for {name}"
            
        permission = Permission(
            id=uuid.uuid4(),
            name=name,
            description=description,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        return permission

    @staticmethod
    def create_user_role(
        user_id: Optional[str] = None,
        role_id: Optional[Union[str, uuid.UUID]] = None
    ) -> UserRole:
        """
        Create a user role association object for testing.
        
        Args:
            user_id: User ID
            role_id: Role ID
            
        Returns:
            UserRole model instance
        """
        if user_id is None:
            user_id = TestDataFactory.create_test_user_id()
            
        if role_id is None:
            role_id = uuid.uuid4()
            
        user_role = UserRole(
            id=uuid.uuid4(),
            user_id=user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(user_id),
            role_id=role_id if isinstance(role_id, uuid.UUID) else uuid.UUID(str(role_id)),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        return user_role
