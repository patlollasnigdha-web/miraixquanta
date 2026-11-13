"""
Tests for MIRAI FastAPI Health and Root Endpoints (M15 / M18)
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_root_endpoint(client):
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ONLINE"
    assert data["api_prefix"] == "/api/v1"
    assert "version" in data


def test_health_endpoint(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert "overall_status" in data
    assert data["overall_status"] in ("HEALTHY", "DEGRADED", "UNHEALTHY")
    assert "components" in data
    assert "backend" in data["components"]
    assert "database" in data["components"]
    assert "ollama" in data["components"]
    assert "models" in data["components"]


def test_openapi_docs_endpoint(client):
    res = client.get("/openapi.json")
    assert res.status_code == 200
    spec = res.json()
    assert "openapi" in spec
    assert "paths" in spec
    assert "/api/v1/health" in spec["paths"]
    assert "/api/v1/decisions/evaluate" in spec["paths"]
    assert "/api/v1/assistant/chat" in spec["paths"]
