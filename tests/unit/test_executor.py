"""Tests for executor."""

import pytest
from datetime import datetime
from xagent.core.executor import Executor


@pytest.mark.asyncio
async def test_executor_initialization():
    """Test executor initialization."""
    executor = Executor()
    assert executor.tool_server is None


@pytest.mark.asyncio
async def test_executor_initialization_with_tool_server():
    """Test executor initialization with tool server."""
    mock_server = object()
    executor = Executor(tool_server=mock_server)
    assert executor.tool_server is mock_server


@pytest.mark.asyncio
async def test_execute_think_action():
    """Test executing think action."""
    executor = Executor()

    plan = {"type": "think", "action": "analyze_situation", "parameters": {"context": "test"}}

    result = await executor.execute(plan)

    assert result["success"] is True
    assert result["action_type"] == "think"
    assert result["action"] == "analyze_situation"
    assert result["output"] is not None
    assert "thought" in result["output"]
    assert result["error"] is None


@pytest.mark.asyncio
async def test_execute_tool_call_without_server():
    """Test executing tool call without tool server."""
    executor = Executor()

    plan = {"type": "tool_call", "action": "search", "parameters": {"query": "test"}}

    result = await executor.execute(plan)

    assert result["success"] is True
    assert result["action_type"] == "tool_call"
    assert "simulated" in result["output"]["message"]


@pytest.mark.asyncio
async def test_execute_tool_call_with_server():
    """Test executing tool call with tool server."""

    class MockToolServer:
        async def call_tool(self, name, params):
            return {"result": f"Called {name}", "params": params}

    executor = Executor(tool_server=MockToolServer())

    plan = {"type": "tool_call", "action": "search", "parameters": {"query": "test"}}

    result = await executor.execute(plan)

    assert result["success"] is True
    assert "Called search" in result["output"]["result"]


@pytest.mark.asyncio
async def test_execute_create_goal():
    """Test executing create goal action."""
    executor = Executor()

    plan = {
        "type": "create_goal",
        "action": "create_goal",
        "parameters": {"content": "New goal description"},
    }

    result = await executor.execute(plan)

    assert result["success"] is True
    assert result["output"]["action"] == "create_goal"
    assert result["output"]["description"] == "New goal description"


@pytest.mark.asyncio
async def test_execute_start_goal():
    """Test executing start goal action."""
    executor = Executor()

    plan = {"type": "start_goal", "action": "start_goal", "parameters": {"goal_id": "goal_123"}}

    result = await executor.execute(plan)

    assert result["success"] is True
    assert result["output"]["action"] == "start_goal"
    assert result["output"]["goal_id"] == "goal_123"


@pytest.mark.asyncio
async def test_execute_unknown_action():
    """Test executing unknown action type."""
    executor = Executor()

    plan = {"type": "unknown_action", "action": "test", "parameters": {}}

    result = await executor.execute(plan)

    assert result["success"] is True
    assert "Unknown action type" in result["output"]["message"]


@pytest.mark.asyncio
async def test_execute_with_exception():
    """Test execution with exception handling."""

    class FailingToolServer:
        async def call_tool(self, name, params):
            raise ValueError("Tool execution failed")

    executor = Executor(tool_server=FailingToolServer())

    plan = {"type": "tool_call", "action": "failing_tool", "parameters": {}}

    result = await executor.execute(plan)

    assert result["success"] is False
    assert result["error"] is not None
    assert "Tool execution failed" in result["error"]


@pytest.mark.asyncio
async def test_execute_result_structure():
    """Test that execute result has correct structure."""
    executor = Executor()

    plan = {"type": "think", "action": "test", "parameters": {}}

    result = await executor.execute(plan)

    # Verify all required fields are present
    assert "action_type" in result
    assert "action" in result
    assert "timestamp" in result
    assert "success" in result
    assert "output" in result
    assert "error" in result
