"""
Integration tests for REST API health check endpoints.

Tests the /health, /healthz, and /ready endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from xagent.api.rest import app


@pytest.fixture
def client():
    """Create test client for the API."""
    return TestClient(app)


def test_health_endpoint_structure(client):
    """Test health endpoint returns proper structure."""
    response = client.get("/health")
    
    # Should return 200 or 503 depending on dependencies
    assert response.status_code in [200, 503]
    
    data = response.json()
    
    # Check required fields
    assert "status" in data
    assert "timestamp" in data
    assert "uptime_seconds" in data
    assert "checks" in data
    assert "version" in data
    
    # Check status values
    assert data["status"] in ["healthy", "degraded", "unhealthy"]
    
    # Check version
    assert data["version"] == "0.1.0"
    
    # Check uptime is a number
    assert isinstance(data["uptime_seconds"], (int, float))
    assert data["uptime_seconds"] >= 0


def test_health_checks_structure(client):
    """Test health endpoint includes all dependency checks."""
    response = client.get("/health")
    data = response.json()
    
    checks = data["checks"]
    
    # Should have checks for all dependencies
    assert "redis" in checks
    assert "postgres" in checks
    assert "chromadb" in checks
    
    # Each check should have status and message
    for check_name, check_data in checks.items():
        assert "status" in check_data
        assert "message" in check_data or check_data["message"] is None
        assert check_data["status"] in ["ok", "failed"]


def test_healthz_liveness_endpoint(client):
    """Test liveness probe endpoint."""
    response = client.get("/healthz")
    
    # Liveness should always return 200 if service is running
    assert response.status_code == 200
    
    data = response.json()
    
    # Check required fields
    assert "alive" in data
    assert "timestamp" in data
    assert "uptime_seconds" in data
    
    # Should always be alive if we got a response
    assert data["alive"] is True
    
    # Check uptime
    assert isinstance(data["uptime_seconds"], (int, float))
    assert data["uptime_seconds"] >= 0


def test_ready_readiness_endpoint(client):
    """Test readiness probe endpoint."""
    response = client.get("/ready")
    
    # Readiness can be 200 (ready) or 503 (not ready)
    assert response.status_code in [200, 503]
    
    data = response.json()
    
    # Check required fields
    assert "ready" in data
    assert "timestamp" in data
    assert "status" in data
    
    # Check ready is boolean
    assert isinstance(data["ready"], bool)
    
    # Status code should match ready state
    if data["ready"]:
        assert response.status_code == 200
    else:
        assert response.status_code == 503


def test_health_endpoint_when_healthy(client):
    """Test health endpoint returns 200 when healthy."""
    response = client.get("/health")
    data = response.json()
    
    # If status is healthy, status code should be 200
    if data["status"] == "healthy":
        assert response.status_code == 200


def test_health_endpoint_when_unhealthy(client):
    """Test health endpoint returns 503 when unhealthy."""
    response = client.get("/health")
    data = response.json()
    
    # If status is unhealthy, status code should be 503
    if data["status"] == "unhealthy":
        assert response.status_code == 503


def test_multiple_health_checks(client):
    """Test multiple health check calls return consistent structure."""
    responses = [client.get("/health") for _ in range(3)]
    
    # All responses should have same structure
    for response in responses:
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data
        assert "checks" in data
        
        # Uptime should increase or stay same
        assert data["uptime_seconds"] >= 0


def test_healthz_multiple_calls(client):
    """Test multiple liveness checks are consistent."""
    responses = [client.get("/healthz") for _ in range(3)]
    
    # All should return 200 and alive=True
    for response in responses:
        assert response.status_code == 200
        data = response.json()
        assert data["alive"] is True


def test_all_health_endpoints_accessible(client):
    """Test all health endpoints are accessible."""
    endpoints = ["/health", "/healthz", "/ready"]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        # Should get a valid response (not 404)
        assert response.status_code != 404
        # Should get JSON response
        assert response.headers["content-type"] == "application/json"


def test_health_timestamp_format(client):
    """Test health check timestamps are in ISO format."""
    import re
    
    # ISO 8601 timestamp pattern
    iso_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
    
    response = client.get("/health")
    data = response.json()
    
    # Timestamp should match ISO format
    assert re.match(iso_pattern, data["timestamp"])


def test_healthz_timestamp_format(client):
    """Test liveness check timestamps are in ISO format."""
    import re
    
    iso_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
    
    response = client.get("/healthz")
    data = response.json()
    
    assert re.match(iso_pattern, data["timestamp"])


def test_ready_timestamp_format(client):
    """Test readiness check timestamps are in ISO format."""
    import re
    
    iso_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
    
    response = client.get("/ready")
    data = response.json()
    
    assert re.match(iso_pattern, data["timestamp"])
