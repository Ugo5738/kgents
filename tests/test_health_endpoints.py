import os
import sys

sys.path.insert(0, os.getcwd())

from fastapi.testclient import TestClient

from main import app


def test_health_endpoints():
    """Test health-check endpoints for all microservices."""
    with TestClient(app) as client:
        endpoints = [
            ("/auth/health", {"status": "auth healthy"}),
            ("/agents/health", {"status": "agents healthy"}),
            ("/tools/health", {"status": "tools healthy"}),
            ("/nl-agents/health", {"status": "nl_agents healthy"}),
            ("/run/health", {"status": "run healthy"}),
        ]
        for path, expected in endpoints:
            resp = client.get(path)
            assert resp.status_code == 200
            assert resp.json() == expected


def test_docs_and_openapi():
    """Test that Swagger UI and OpenAPI JSON are served."""
    with TestClient(app) as client:
        resp = client.get("/docs")
        assert resp.status_code == 200
        assert "swagger-ui" in resp.text.lower()

        resp2 = client.get("/openapi.json")
        assert resp2.status_code == 200
        data = resp2.json()
        assert "openapi" in data
        assert data["info"]["title"] == "Kgents (Agent-as-a-Service) Platform"
