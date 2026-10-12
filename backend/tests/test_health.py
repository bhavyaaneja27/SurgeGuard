import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)


def test_health_endpoint():
    """
    Verify GET /health contract according to PRD Section 12:
    status, version, model_status, database_status.
    """
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == settings.APP_VERSION
    assert "model_status" in data
    assert "database_status" in data
    assert "timestamp" in data


def test_api_v1_health_endpoint():
    """
    Verify GET /api/v1/health versioned route functions identically.
    """
    response = client.get(f"{settings.API_V1_PREFIX}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == settings.APP_VERSION


def test_root_summary_endpoint():
    """
    Verify GET / returns service information and synthetic disclaimer.
    """
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == settings.APP_NAME
    assert data["data_mode"] == "SYNTHETIC_SIMULATION"
    assert "disclaimer" in data


def test_not_found_returns_standard_error_shape():
    """
    Verify 404 error format conforms to PRD Section 12.1 error contract:
    { "error_code": "...", "message": "...", "details": ... }
    """
    response = client.get("/api/v1/non_existent_route")
    assert response.status_code == 404
    data = response.json()
    assert "error_code" in data
    assert data["error_code"] == "HTTP_404"
    assert "message" in data
