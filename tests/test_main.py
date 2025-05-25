import os
import sys

sys.path.insert(0, os.getcwd())

from fastapi.testclient import TestClient

from main import app


def test_root_endpoint():
    """Test that the root endpoint returns a welcome message and status 200."""
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {
            "message": "Welcome to the Kgents (Agent-as-a-Service) Platform"
        }
