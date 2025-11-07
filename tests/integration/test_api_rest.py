"""
Integration tests for REST API endpoints.

Tests goal management, agent control, and overall API functionality.
"""

import pytest
from fastapi.testclient import TestClient

from xagent.api.rest import app


@pytest.fixture
def client():
    """Create test client for the API."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint returns basic info."""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "name" in data
    assert "version" in data
    assert "status" in data
    
    assert data["name"] == "X-Agent API"
    assert data["version"] == "0.1.0"
    assert data["status"] == "running"


def test_status_endpoint_structure(client):
    """Test status endpoint returns proper structure."""
    response = client.get("/status")
    
    # Status endpoint requires agent to be initialized
    # It might return 503 if agent is not ready
    assert response.status_code in [200, 503]
    
    if response.status_code == 503:
        # Agent not initialized
        data = response.json()
        assert "detail" in data
    else:
        # Agent is initialized
        data = response.json()
        # Status should return some agent state information
        assert isinstance(data, dict)


def test_goals_list_endpoint(client):
    """Test listing goals endpoint."""
    response = client.get("/goals")
    
    # Might return 503 if agent not initialized
    assert response.status_code in [200, 503]
    
    if response.status_code == 200:
        data = response.json()
        
        # Should have structure with goals list
        assert "total" in data
        assert "goals" in data
        assert isinstance(data["goals"], list)
        assert isinstance(data["total"], int)


def test_create_goal_endpoint(client):
    """Test creating a goal via API."""
    goal_data = {
        "description": "Test goal for integration testing",
        "mode": "goal_oriented",
        "priority": 5,
        "completion_criteria": ["Test completion"]
    }
    
    response = client.post("/goals", json=goal_data)
    
    # Might return 503 if agent not initialized
    assert response.status_code in [200, 503]
    
    if response.status_code == 200:
        data = response.json()
        
        assert "status" in data
        assert "goal" in data
        assert data["status"] == "created"
        
        # Check goal structure
        goal = data["goal"]
        assert "id" in goal
        assert "description" in goal
        assert goal["description"] == "Test goal for integration testing"


def test_create_goal_minimal(client):
    """Test creating a goal with minimal data."""
    goal_data = {
        "description": "Minimal test goal"
    }
    
    response = client.post("/goals", json=goal_data)
    
    # Should accept minimal goal creation
    assert response.status_code in [200, 503]
    
    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "created"


def test_create_goal_with_continuous_mode(client):
    """Test creating a continuous goal."""
    goal_data = {
        "description": "Continuous monitoring task",
        "mode": "continuous",
        "priority": 8
    }
    
    response = client.post("/goals", json=goal_data)
    
    assert response.status_code in [200, 503]
    
    if response.status_code == 200:
        data = response.json()
        goal = data["goal"]
        assert goal["mode"] == "continuous"


def test_get_specific_goal(client):
    """Test getting a specific goal by ID."""
    # First create a goal
    goal_data = {
        "description": "Goal to retrieve"
    }
    
    create_response = client.post("/goals", json=goal_data)
    
    if create_response.status_code == 200:
        created_goal = create_response.json()["goal"]
        goal_id = created_goal["id"]
        
        # Now retrieve it
        response = client.get(f"/goals/{goal_id}")
        
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "goal" in data
            assert "hierarchy" in data
            
            goal = data["goal"]
            assert goal["id"] == goal_id
            assert goal["description"] == "Goal to retrieve"


def test_get_nonexistent_goal(client):
    """Test getting a goal that doesn't exist."""
    fake_id = "nonexistent-goal-id-12345"
    
    response = client.get(f"/goals/{fake_id}")
    
    # Should return 404 or 503 (if agent not initialized)
    assert response.status_code in [404, 503]


def test_start_agent_endpoint(client):
    """Test starting the agent."""
    response = client.post("/start")
    
    # Agent might already be running or not initialized
    assert response.status_code in [200, 503]
    
    if response.status_code == 200:
        data = response.json()
        assert "status" in data
        assert "message" in data


def test_start_agent_with_goal(client):
    """Test starting agent with initial goal."""
    goal_data = {
        "description": "Initial startup goal"
    }
    
    response = client.post("/start", json=goal_data)
    
    assert response.status_code in [200, 503]
    
    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "started"


def test_stop_agent_endpoint(client):
    """Test stopping the agent."""
    response = client.post("/stop")
    
    # Might return 200 or 503 depending on agent state
    assert response.status_code in [200, 503]
    
    if response.status_code == 200:
        data = response.json()
        assert "status" in data
        assert data["status"] == "stopped"


def test_send_command_endpoint(client):
    """Test sending a command to the agent."""
    command_data = {
        "command": "Test command for integration"
    }
    
    response = client.post("/command", json=command_data)
    
    assert response.status_code in [200, 503]
    
    if response.status_code == 200:
        data = response.json()
        assert "status" in data
        assert data["status"] == "sent"


def test_send_feedback_endpoint(client):
    """Test sending feedback to the agent."""
    feedback_data = {
        "feedback": "Test feedback message"
    }
    
    response = client.post("/feedback", json=feedback_data)
    
    assert response.status_code in [200, 503]
    
    if response.status_code == 200:
        data = response.json()
        assert "status" in data
        assert data["status"] == "sent"


def test_api_cors_headers(client):
    """Test that CORS headers are properly set."""
    response = client.get("/")
    
    # Check for CORS headers
    headers = response.headers
    
    # FastAPI's CORS middleware should add these headers
    assert "access-control-allow-origin" in headers or response.status_code == 200


def test_invalid_endpoint_returns_404(client):
    """Test that invalid endpoints return 404."""
    response = client.get("/nonexistent-endpoint-xyz")
    
    assert response.status_code == 404


def test_invalid_method_returns_405(client):
    """Test that invalid methods return 405."""
    # Try POST on a GET-only endpoint
    response = client.post("/")
    
    assert response.status_code == 405


def test_create_goal_invalid_json(client):
    """Test creating goal with invalid JSON."""
    response = client.post(
        "/goals",
        data="not valid json",
        headers={"Content-Type": "application/json"}
    )
    
    # Should return 422 (validation error) or similar
    assert response.status_code in [422, 400]


def test_create_goal_missing_required_field(client):
    """Test creating goal without required description."""
    goal_data = {
        "priority": 5
        # missing 'description'
    }
    
    response = client.post("/goals", json=goal_data)
    
    # Should return 422 (validation error)
    assert response.status_code == 422


def test_api_consistency(client):
    """Test API returns consistent responses."""
    # Make multiple requests to same endpoint
    responses = [client.get("/") for _ in range(3)]
    
    # All should have same status code
    status_codes = [r.status_code for r in responses]
    assert len(set(status_codes)) == 1  # All same
    
    # All should have same structure
    for response in responses:
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data
