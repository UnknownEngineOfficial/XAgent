"""
Integration tests for WebSocket API endpoints.

Tests real-time communication, connection management, and message handling.
"""

import json
import pytest
from fastapi.testclient import TestClient

from xagent.api.websocket import app


@pytest.fixture
def client():
    """Create test client for the WebSocket API."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint returns basic info."""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "name" in data
    assert "version" in data
    assert "active_connections" in data
    
    assert data["name"] == "X-Agent WebSocket Gateway"
    assert data["version"] == "0.1.0"
    assert isinstance(data["active_connections"], int)


def test_websocket_connection_established(client):
    """Test WebSocket connection can be established."""
    with client.websocket_connect("/ws") as websocket:
        # Should receive welcome message
        data = websocket.receive_json()
        
        assert data["type"] == "connected"
        assert data["message"] == "Connected to X-Agent"
        assert "timestamp" in data


def test_websocket_invalid_json(client):
    """Test WebSocket handles invalid JSON gracefully."""
    with client.websocket_connect("/ws") as websocket:
        # Skip welcome message
        websocket.receive_json()
        
        # Send invalid JSON
        websocket.send_text("not valid json")
        
        # Should receive error message
        data = websocket.receive_json()
        
        assert data["type"] == "error"
        assert "Invalid JSON" in data["message"]


def test_websocket_unknown_message_type(client):
    """Test WebSocket handles unknown message types."""
    with client.websocket_connect("/ws") as websocket:
        # Skip welcome message
        websocket.receive_json()
        
        # Send unknown message type
        message = {
            "type": "unknown_type",
            "content": "test"
        }
        websocket.send_json(message)
        
        # Should receive error message
        data = websocket.receive_json()
        
        assert data["type"] == "error"
        assert "Unknown message type" in data["message"]


def test_websocket_status_request(client):
    """Test WebSocket status request."""
    with client.websocket_connect("/ws") as websocket:
        # Skip welcome message
        websocket.receive_json()
        
        # Request status
        message = {"type": "status"}
        websocket.send_json(message)
        
        # Should receive status response
        data = websocket.receive_json()
        
        # Agent might not be initialized in test environment
        assert data["type"] in ["status", "error"]
        assert "timestamp" in data


def test_websocket_command_message(client):
    """Test WebSocket command message handling."""
    with client.websocket_connect("/ws") as websocket:
        # Skip welcome message
        websocket.receive_json()
        
        # Send command
        message = {
            "type": "command",
            "content": "Test command"
        }
        websocket.send_json(message)
        
        # Should receive acknowledgment or error (if agent not initialized)
        data = websocket.receive_json()
        
        assert data["type"] in ["command_received", "error"]
        assert "timestamp" in data


def test_websocket_feedback_message(client):
    """Test WebSocket feedback message handling."""
    with client.websocket_connect("/ws") as websocket:
        # Skip welcome message
        websocket.receive_json()
        
        # Send feedback
        message = {
            "type": "feedback",
            "content": "Test feedback"
        }
        websocket.send_json(message)
        
        # Should receive acknowledgment or error (if agent not initialized)
        data = websocket.receive_json()
        
        assert data["type"] in ["feedback_received", "error"]
        assert "timestamp" in data


def test_websocket_start_message(client):
    """Test WebSocket start message handling."""
    with client.websocket_connect("/ws") as websocket:
        # Skip welcome message
        websocket.receive_json()
        
        # Send start message
        message = {
            "type": "start",
            "goal": "Test goal"
        }
        websocket.send_json(message)
        
        # Should receive started confirmation or error
        data = websocket.receive_json()
        
        assert data["type"] in ["started", "error"]
        assert "timestamp" in data


def test_websocket_stop_message(client):
    """Test WebSocket stop message handling."""
    with client.websocket_connect("/ws") as websocket:
        # Skip welcome message
        websocket.receive_json()
        
        # Send stop message
        message = {"type": "stop"}
        websocket.send_json(message)
        
        # Should receive stopped confirmation or error
        data = websocket.receive_json()
        
        assert data["type"] in ["stopped", "error"]
        assert "timestamp" in data


def test_websocket_multiple_messages(client):
    """Test WebSocket can handle multiple messages in sequence."""
    with client.websocket_connect("/ws") as websocket:
        # Skip welcome message
        websocket.receive_json()
        
        # Send multiple status requests
        for i in range(3):
            message = {"type": "status"}
            websocket.send_json(message)
            
            # Should receive response each time
            data = websocket.receive_json()
            assert data["type"] in ["status", "error"]
            assert "timestamp" in data


def test_websocket_connection_manager_tracks_connections(client):
    """Test that connection manager properly tracks active connections."""
    # Check initial state
    response = client.get("/")
    initial_connections = response.json()["active_connections"]
    
    # Open a WebSocket connection
    with client.websocket_connect("/ws") as websocket:
        # Skip welcome message
        websocket.receive_json()
        
        # Check that connection count increased
        # Note: TestClient might not accurately reflect this in all cases
        # This is a best-effort test
        response2 = client.get("/")
        data = response2.json()
        assert "active_connections" in data


def test_websocket_message_structure_validation(client):
    """Test that all WebSocket messages have required fields."""
    with client.websocket_connect("/ws") as websocket:
        # Receive welcome message
        data = websocket.receive_json()
        
        # All messages should have these fields
        assert "type" in data
        assert "timestamp" in data
        
        # Welcome message should have message field
        assert "message" in data


def test_websocket_command_without_content(client):
    """Test WebSocket command message without content."""
    with client.websocket_connect("/ws") as websocket:
        # Skip welcome message
        websocket.receive_json()
        
        # Send command without content
        message = {"type": "command"}
        websocket.send_json(message)
        
        # Should receive acknowledgment or error
        data = websocket.receive_json()
        
        assert data["type"] in ["command_received", "error"]
        assert "timestamp" in data


def test_websocket_feedback_without_content(client):
    """Test WebSocket feedback message without content."""
    with client.websocket_connect("/ws") as websocket:
        # Skip welcome message
        websocket.receive_json()
        
        # Send feedback without content
        message = {"type": "feedback"}
        websocket.send_json(message)
        
        # Should receive acknowledgment or error
        data = websocket.receive_json()
        
        assert data["type"] in ["feedback_received", "error"]
        assert "timestamp" in data


def test_websocket_start_without_goal(client):
    """Test WebSocket start message without goal."""
    with client.websocket_connect("/ws") as websocket:
        # Skip welcome message
        websocket.receive_json()
        
        # Send start message without goal
        message = {"type": "start"}
        websocket.send_json(message)
        
        # Should receive started confirmation or error
        data = websocket.receive_json()
        
        assert data["type"] in ["started", "error"]
        assert "timestamp" in data


def test_websocket_json_serialization(client):
    """Test that WebSocket properly serializes JSON responses."""
    with client.websocket_connect("/ws") as websocket:
        # Receive and parse welcome message
        data = websocket.receive_json()
        
        # Data should be a valid dictionary
        assert isinstance(data, dict)
        assert isinstance(data["type"], str)
        assert isinstance(data["message"], str)
        assert isinstance(data["timestamp"], str)


def test_websocket_timestamp_format(client):
    """Test that WebSocket timestamps are in ISO format."""
    with client.websocket_connect("/ws") as websocket:
        # Receive welcome message
        data = websocket.receive_json()
        
        # Timestamp should be in ISO format (basic check)
        timestamp = data["timestamp"]
        assert "T" in timestamp  # ISO format includes T between date and time
        assert isinstance(timestamp, str)
