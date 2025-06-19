"""
Pytest configuration for End-to-End tests across the Kgents platform.
Provides fixtures for running all required services and generating test data.
"""
import os
import uuid
import pytest
import asyncio
import subprocess
import time
from typing import Dict, List, Any, AsyncGenerator, Optional
from httpx import AsyncClient
import json
import signal
from pathlib import Path


class ServiceManager:
    """Manages starting and stopping microservices for E2E testing."""
    
    def __init__(self):
        self.services = {}
        self.project_root = Path("/Users/i/Documents/work/kgents")
    
    async def start_service(self, service_name: str, port: int) -> subprocess.Popen:
        """Start a service on the specified port."""
        service_dir = self.project_root / service_name
        
        # Set up environment variables for testing
        env = os.environ.copy()
        env["TESTING"] = "true"
        env["SUPABASE_URL"] = os.environ.get("SUPABASE_URL") or "http://localhost:54321"
        env["SUPABASE_ANON_KEY"] = os.environ.get("SUPABASE_ANON_KEY") or "mock-anon-key"
        env["PYTHONPATH"] = f"{self.project_root}:{service_dir}"
        env["TEST_PORT"] = str(port)
        
        # Start the service
        print(f"Starting {service_name} on port {port}...")
        cmd = ["uvicorn", f"{service_name}.main:app", "--host", "127.0.0.1", "--port", str(port)]
        
        process = subprocess.Popen(
            cmd,
            cwd=service_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Store process for later cleanup
        self.services[service_name] = process
        
        # Wait for service to be ready
        await self._wait_for_service(port)
        
        return process
    
    async def _wait_for_service(self, port: int, max_retries: int = 10, delay: int = 1):
        """Wait for a service to be available on the specified port."""
        base_url = f"http://127.0.0.1:{port}"
        
        for i in range(max_retries):
            try:
                async with AsyncClient() as client:
                    response = await client.get(f"{base_url}/health")
                    if response.status_code == 200:
                        print(f"Service on port {port} is ready!")
                        return
            except Exception:
                pass
            
            print(f"Waiting for service on port {port}... ({i+1}/{max_retries})")
            await asyncio.sleep(delay)
        
        raise TimeoutError(f"Service on port {port} did not become available")
    
    def stop_all_services(self):
        """Stop all running services."""
        for name, process in self.services.items():
            print(f"Stopping {name}...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def service_manager():
    """Fixture to manage services for E2E tests."""
    manager = ServiceManager()
    yield manager
    manager.stop_all_services()


@pytest.fixture(scope="session")
async def e2e_environment(service_manager):
    """
    Start all required services for E2E testing.
    Returns URLs for each service.
    """
    # Start required services
    await service_manager.start_service("auth_service", 8000)
    await service_manager.start_service("agent_management_service", 8001)
    # Add more services as needed
    
    # Return service URLs
    yield {
        "auth_service_url": "http://127.0.0.1:8000",
        "agent_service_url": "http://127.0.0.1:8001"
    }


@pytest.fixture(scope="session")
async def e2e_auth_client(e2e_environment):
    """Create a client for auth service."""
    async with AsyncClient(base_url=e2e_environment["auth_service_url"]) as client:
        yield client


@pytest.fixture(scope="session")
async def e2e_agent_client(e2e_environment):
    """Create a client for agent management service."""
    async with AsyncClient(base_url=e2e_environment["agent_service_url"]) as client:
        yield client


@pytest.fixture(scope="session")
async def test_user(e2e_auth_client):
    """Create a test user and return credentials."""
    user_id = str(uuid.uuid4())
    username = f"e2e_user_{user_id[:8]}"
    email = f"{username}@example.com"
    password = "SecureE2EPassword123!"
    
    # Register user
    user_data = {
        "email": email,
        "password": password,
        "username": username,
        "first_name": "E2E",
        "last_name": "Test"
    }
    
    response = await e2e_auth_client.post("/api/v1/auth/users/register", json=user_data)
    assert response.status_code in (201, 200), f"Failed to create test user: {response.text}"
    
    # Return user credentials
    yield {
        "email": email,
        "password": password,
        "username": username
    }


@pytest.fixture(scope="session")
async def auth_token(e2e_auth_client, test_user):
    """Get authentication token for test user."""
    login_data = {
        "username": test_user["email"],
        "password": test_user["password"]
    }
    
    response = await e2e_auth_client.post("/api/v1/auth/users/login", data=login_data)
    assert response.status_code == 200, f"Failed to login: {response.text}"
    
    token_data = response.json()
    assert "access_token" in token_data, "No access token in response"
    
    yield token_data["access_token"]
