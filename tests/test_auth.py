import os
import sys

sys.path.insert(0, os.getcwd())

import pytest
from fastapi.testclient import TestClient

from app.db import crud_users
from app.models.user import UserCreate, UserLogin
from main import app


@pytest.fixture(autouse=True)
def dummy_user_crud(monkeypatch):
    """Stub user CRUD functions for testing without Supabase."""
    storage: dict = {}

    async def dummy_create_user(user_create: UserCreate):
        user = {"id": 1, "email": user_create.email}
        storage['user'] = user
        from app.models.user import UserResponse
        return UserResponse(**user)

    async def dummy_authenticate_user(user_login: UserLogin):
        if 'user' in storage and storage['user']['email'] == user_login.email:
            from app.models.user import UserResponse
            return UserResponse(**storage['user'])
        return None

    async def dummy_get_user_by_id(user_id: int):
        if 'user' in storage and storage['user']['id'] == user_id:
            from app.models.user import UserResponse
            return UserResponse(**storage['user'])
        return None

    monkeypatch.setattr('app.api.v1.auth.create_user', dummy_create_user)
    monkeypatch.setattr('app.api.v1.auth.authenticate_user', dummy_authenticate_user)
    monkeypatch.setattr('app.api.v1.auth.get_user_by_id', dummy_get_user_by_id)


def test_register_login_me_flow():
    """Test user registration, login, and accessing protected endpoint."""
    with TestClient(app) as client:
        # Register
        resp = client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "secret"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == 1
        assert data["email"] == "test@example.com"

        # Login
        resp = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "secret"},
        )
        assert resp.status_code == 200
        token_data = resp.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        access_token = token_data["access_token"]

        # Access protected /me
        resp = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        me_data = resp.json()
        assert me_data == data 