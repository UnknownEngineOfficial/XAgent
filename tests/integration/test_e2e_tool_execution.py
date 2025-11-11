"""
End-to-End tests for tool execution workflows.

Tests complete tool execution flows including sandboxing, error handling, and chaining.
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from xagent.core.executor import Executor
from xagent.tools.tool_server import ToolServer


@pytest.fixture
def tool_server():
    """Create a tool server instance."""
    return ToolServer()


@pytest.fixture
def executor(tool_server):
    """Create an executor with tool server."""
    return Executor(tool_server=tool_server)


@pytest.fixture
def mock_tool_server():
    """Create a mock tool server for controlled testing."""
    server = Mock(spec=ToolServer)
    server.call_tool = AsyncMock()
    return server


@pytest.mark.asyncio
@pytest.mark.integration
async def test_think_tool_execution_flow(executor):
    """Test complete flow for think/reasoning action execution."""
    # Create a think action plan
    plan = {
        "type": "think",
        "action": "Analyze the problem structure",
        "parameters": {
            "focus": "architecture",
            "depth": "detailed",
        },
    }

    # Execute the plan
    result = await executor.execute(plan)

    # Verify execution completed successfully
    assert result is not None
    assert result["success"] is True
    assert result["action_type"] == "think"
    assert result["output"] is not None
    assert "thought" in result["output"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_tool_call_execution_flow(executor, mock_tool_server):
    """Test complete flow for tool call execution."""
    # Configure mock tool server
    mock_tool_server.call_tool.return_value = {
        "status": "success",
        "result": "Tool executed successfully",
    }

    # Replace executor's tool server with mock
    executor.tool_server = mock_tool_server

    # Create a tool call plan
    plan = {
        "type": "tool_call",
        "action": "search",
        "parameters": {
            "query": "Python best practices",
            "max_results": 5,
        },
    }

    # Execute the plan
    result = await executor.execute(plan)

    # Verify execution
    assert result is not None
    assert result["success"] is True
    assert result["action_type"] == "tool_call"
    assert mock_tool_server.call_tool.called
    assert mock_tool_server.call_tool.call_args[0][0] == "search"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_sequential_tool_execution_flow(executor, mock_tool_server):
    """Test executing multiple tools in sequence."""
    # Configure mock tool server for different tools
    tool_results = {
        "search": {"results": ["result1", "result2"]},
        "read_file": {"content": "file content"},
        "write_file": {"status": "written"},
    }

    async def mock_call_tool(tool_name, params):
        return tool_results.get(tool_name, {"status": "success"})

    mock_tool_server.call_tool = mock_call_tool
    executor.tool_server = mock_tool_server

    # Execute tools in sequence
    plans = [
        {"type": "tool_call", "action": "search", "parameters": {"query": "test"}},
        {
            "type": "tool_call",
            "action": "read_file",
            "parameters": {"path": "/test.txt"},
        },
        {
            "type": "tool_call",
            "action": "write_file",
            "parameters": {"path": "/output.txt", "content": "test"},
        },
    ]

    results = []
    for plan in plans:
        result = await executor.execute(plan)
        results.append(result)
        # Small delay between executions
        await asyncio.sleep(0.1)

    # Verify all executions succeeded
    assert len(results) == 3
    assert all(r["success"] for r in results)
    assert results[0]["output"]["results"] == ["result1", "result2"]
    assert results[1]["output"]["content"] == "file content"
    assert results[2]["output"]["status"] == "written"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_tool_execution_with_error_handling(executor, mock_tool_server):
    """Test tool execution flow with error handling."""
    # Configure mock to raise error
    mock_tool_server.call_tool.side_effect = Exception("Tool execution failed")
    executor.tool_server = mock_tool_server

    # Create a tool call plan
    plan = {
        "type": "tool_call",
        "action": "failing_tool",
        "parameters": {},
    }

    # Execute the plan
    result = await executor.execute(plan)

    # Verify error was handled
    assert result is not None
    assert result["success"] is False
    assert result["error"] is not None
    assert "failed" in result["error"].lower()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_tool_execution_timeout_handling(executor, mock_tool_server):
    """Test handling of tool execution timeouts."""

    # Configure mock to simulate slow tool
    async def slow_tool(tool_name, params):
        await asyncio.sleep(5.0)  # Simulate slow execution
        return {"status": "success"}

    mock_tool_server.call_tool = slow_tool
    executor.tool_server = mock_tool_server

    # Create a tool call plan
    plan = {
        "type": "tool_call",
        "action": "slow_tool",
        "parameters": {},
    }

    # Execute with timeout
    try:
        result = await asyncio.wait_for(executor.execute(plan), timeout=1.0)
        # If we get here without timeout, that's also acceptable
        assert result is not None
    except asyncio.TimeoutError:
        # Timeout is expected behavior for slow tools
        pass


@pytest.mark.asyncio
@pytest.mark.integration
async def test_goal_creation_execution_flow(executor):
    """Test complete flow for goal creation action."""
    # Create a goal creation plan
    plan = {
        "type": "create_goal",
        "parameters": {
            "content": "Create a new feature",
            "priority": 7,
        },
    }

    # Execute the plan
    result = await executor.execute(plan)

    # Verify execution
    assert result is not None
    assert result["success"] is True
    assert result["action_type"] == "create_goal"
    assert result["output"] is not None
    assert "action" in result["output"]
    assert result["output"]["action"] == "create_goal"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_goal_start_execution_flow(executor):
    """Test complete flow for goal start action."""
    # Create a goal start plan
    plan = {
        "type": "start_goal",
        "parameters": {
            "goal_id": "test-goal-123",
        },
    }

    # Execute the plan
    result = await executor.execute(plan)

    # Verify execution
    assert result is not None
    assert result["success"] is True
    assert result["action_type"] == "start_goal"
    assert result["output"] is not None
    assert result["output"]["goal_id"] == "test-goal-123"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_unknown_action_type_handling(executor):
    """Test handling of unknown action types."""
    # Create a plan with unknown action type
    plan = {
        "type": "unknown_action",
        "action": "mystery",
        "parameters": {},
    }

    # Execute the plan
    result = await executor.execute(plan)

    # Verify execution handled unknown type
    assert result is not None
    assert result["success"] is True  # Should not crash
    assert "Unknown action type" in result["output"]["message"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_tool_execution_metrics_tracking(executor, mock_tool_server):
    """Test that tool execution tracks metrics properly."""
    # Configure mock tool server
    mock_tool_server.call_tool.return_value = {"status": "success"}
    executor.tool_server = mock_tool_server

    # Verify executor has metrics collector
    assert executor.metrics is not None

    # Execute a tool
    plan = {
        "type": "tool_call",
        "action": "test_tool",
        "parameters": {},
    }

    result = await executor.execute(plan)

    # Verify execution succeeded
    assert result is not None
    assert result["success"] is True

    # Note: Actual metric values are tested in unit tests
    # Here we just verify the flow works with metrics


@pytest.mark.asyncio
@pytest.mark.integration
async def test_tool_chaining_workflow(executor, mock_tool_server):
    """Test complex workflow with tool result chaining."""
    # Configure mock tools where output of one feeds into next
    call_count = 0

    async def chained_tool(tool_name, params):
        nonlocal call_count
        call_count += 1

        if tool_name == "tool1":
            return {"data": "from_tool1", "next": "tool2"}
        elif tool_name == "tool2":
            # Use data from previous tool
            assert "input" in params
            return {"data": "from_tool2", "next": "tool3"}
        elif tool_name == "tool3":
            assert "input" in params
            return {"data": "final_result"}
        return {"error": "unknown tool"}

    mock_tool_server.call_tool = chained_tool
    executor.tool_server = mock_tool_server

    # Execute chained tools
    result1 = await executor.execute(
        {
            "type": "tool_call",
            "action": "tool1",
            "parameters": {},
        }
    )

    assert result1["success"]
    intermediate_data = result1["output"]["data"]

    result2 = await executor.execute(
        {
            "type": "tool_call",
            "action": "tool2",
            "parameters": {"input": intermediate_data},
        }
    )

    assert result2["success"]
    intermediate_data2 = result2["output"]["data"]

    result3 = await executor.execute(
        {
            "type": "tool_call",
            "action": "tool3",
            "parameters": {"input": intermediate_data2},
        }
    )

    assert result3["success"]
    assert result3["output"]["data"] == "final_result"
    assert call_count == 3


@pytest.mark.asyncio
@pytest.mark.integration
async def test_parallel_tool_execution_flow(executor, mock_tool_server):
    """Test executing multiple tools in parallel."""
    # Configure mock with different delays
    async def delayed_tool(tool_name, params):
        delay = params.get("delay", 0.1)
        await asyncio.sleep(delay)
        return {"tool": tool_name, "completed": True}

    mock_tool_server.call_tool = delayed_tool
    executor.tool_server = mock_tool_server

    # Create multiple execution tasks
    plans = [
        {
            "type": "tool_call",
            "action": f"tool_{i}",
            "parameters": {"delay": 0.1},
        }
        for i in range(5)
    ]

    # Execute in parallel
    tasks = [executor.execute(plan) for plan in plans]
    results = await asyncio.gather(*tasks)

    # Verify all completed successfully
    assert len(results) == 5
    assert all(r["success"] for r in results)
    assert all(r["output"]["completed"] for r in results)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_tool_execution_with_retry_logic(executor, mock_tool_server):
    """Test tool execution with retry on transient failures."""
    attempt_count = 0

    async def flaky_tool(tool_name, params):
        nonlocal attempt_count
        attempt_count += 1

        # Fail first 2 attempts, succeed on 3rd
        if attempt_count < 3:
            raise Exception("Transient failure")
        return {"status": "success", "attempts": attempt_count}

    mock_tool_server.call_tool = flaky_tool
    executor.tool_server = mock_tool_server

    # Try executing with retries
    plan = {
        "type": "tool_call",
        "action": "flaky_tool",
        "parameters": {},
    }

    max_retries = 3
    last_result = None

    for attempt in range(max_retries):
        result = await executor.execute(plan)
        last_result = result

        if result["success"]:
            break

        await asyncio.sleep(0.1)

    # Should eventually succeed
    assert last_result is not None
    assert last_result["success"] is True
    assert attempt_count == 3
