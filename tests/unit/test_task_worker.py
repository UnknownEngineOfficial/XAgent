"""Tests for Celery worker tasks."""

import pytest
from unittest.mock import MagicMock, patch, Mock

from xagent.tasks.worker import (
    execute_cognitive_loop,
    execute_tool,
    process_goal,
    cleanup_memory,
)


class TestExecuteCognitiveLoop:
    """Tests for execute_cognitive_loop task."""

    @patch("xagent.core.agent.XAgent")
    @patch("xagent.core.goal_engine.GoalEngine")
    def test_execute_cognitive_loop_success(self, mock_goal_engine, mock_agent):
        """Test successful cognitive loop execution."""
        # Setup mocks
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_agent_instance.think_and_act.return_value = {
            "should_stop": False,
            "actions": ["action1"],
        }

        # Execute task
        result = execute_cognitive_loop(
            agent_id="test-agent",
            max_iterations=2,
        )

        # Verify results
        assert result["status"] == "success"
        assert result["iterations"] == 2
        assert result["actions_executed"] >= 0

    @patch("xagent.core.agent.XAgent")
    @patch("xagent.core.goal_engine.GoalEngine")
    def test_execute_cognitive_loop_early_stop(self, mock_goal_engine, mock_agent):
        """Test cognitive loop with early stopping."""
        # Setup mocks
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_agent_instance.think_and_act.return_value = {
            "should_stop": True,
            "actions": [],
        }

        # Execute task
        result = execute_cognitive_loop(
            agent_id="test-agent",
            max_iterations=10,
        )

        # Verify results
        assert result["status"] == "success"
        assert result["iterations"] == 1  # Stopped after first iteration

    @patch("xagent.core.agent.XAgent")
    @patch("xagent.core.goal_engine.GoalEngine")
    def test_execute_cognitive_loop_with_goal(self, mock_goal_engine, mock_agent):
        """Test cognitive loop with specific goal."""
        # Setup mocks
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_agent_instance.think_and_act.return_value = {
            "should_stop": True,
            "goal_completed": True,
        }

        # Execute task
        result = execute_cognitive_loop(
            agent_id="test-agent",
            goal_id="goal-123",
            max_iterations=5,
        )

        # Verify results
        assert result["status"] == "success"
        assert result["goals_completed"] >= 0

    @patch("xagent.core.agent.XAgent")
    @patch("xagent.core.goal_engine.GoalEngine")
    def test_execute_cognitive_loop_iteration_error(self, mock_goal_engine, mock_agent):
        """Test cognitive loop with error during iteration."""
        # Setup mocks
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_agent_instance.think_and_act.side_effect = Exception("Test error")

        # Execute task
        result = execute_cognitive_loop(
            agent_id="test-agent",
            max_iterations=3,
        )

        # Verify partial completion
        assert result["status"] == "partial"
        assert result["error"] is not None


class TestExecuteTool:
    """Tests for execute_tool task."""

    @patch("xagent.tools.langserve_tools.get_tool_by_name")
    def test_execute_tool_success(self, mock_get_tool):
        """Test successful tool execution."""
        # Setup mock tool
        mock_tool = MagicMock()
        mock_tool.return_value = {"output": "tool result"}
        mock_get_tool.return_value = mock_tool

        # Execute task
        result = execute_tool(
            tool_name="test_tool",
            tool_args={"arg1": "value1"},
        )

        # Verify results
        assert result["status"] == "success"
        assert result["result"] == {"output": "tool result"}
        assert result["error"] is None

        # Verify tool was called with correct args
        mock_tool.assert_called_once_with(arg1="value1")

    @patch("xagent.tools.langserve_tools.get_tool_by_name")
    def test_execute_tool_not_found(self, mock_get_tool):
        """Test tool execution when tool doesn't exist."""
        mock_get_tool.return_value = None

        # Execute task
        result = execute_tool(
            tool_name="nonexistent_tool",
            tool_args={},
        )

        # Verify failure
        assert result["status"] == "failure"
        assert "not found" in result["error"].lower()

    @patch("xagent.tools.langserve_tools.get_tool_by_name")
    def test_execute_tool_with_agent_id(self, mock_get_tool):
        """Test tool execution with agent context."""
        mock_tool = MagicMock()
        mock_tool.return_value = "result"
        mock_get_tool.return_value = mock_tool

        # Execute task
        result = execute_tool(
            tool_name="test_tool",
            tool_args={"arg1": "value1"},
            agent_id="test-agent",
        )

        # Verify success
        assert result["status"] == "success"

    @patch("xagent.tools.langserve_tools.get_tool_by_name")
    def test_execute_tool_execution_error(self, mock_get_tool):
        """Test tool execution with runtime error."""
        mock_tool = MagicMock()
        mock_tool.side_effect = RuntimeError("Tool failed")
        mock_get_tool.return_value = mock_tool

        # Execute task
        result = execute_tool(
            tool_name="failing_tool",
            tool_args={},
        )

        # Verify failure
        assert result["status"] == "failure"
        assert result["error"] is not None


class TestProcessGoal:
    """Tests for process_goal task."""

    @patch("xagent.core.planner.Planner")
    @patch("xagent.core.goal_engine.GoalEngine")
    def test_process_goal_success(self, mock_goal_engine_class, mock_planner_class):
        """Test successful goal processing."""
        # Setup mocks
        mock_goal_engine = MagicMock()
        mock_goal_engine_class.return_value = mock_goal_engine

        mock_goal = MagicMock()
        mock_goal.status = "in_progress"
        mock_goal.priority = 5
        mock_goal_engine.get_goal.return_value = mock_goal

        mock_planner = MagicMock()
        mock_planner_class.return_value = mock_planner
        mock_planner.create_plan.return_value = {"sub_goals": ["sub-goal-1", "sub-goal-2"]}

        # Execute task
        result = process_goal(goal_id="goal-123")

        # Verify results
        assert result["status"] == "success"
        assert result["sub_goals_created"] == 2

    @patch("xagent.tasks.worker.logger")  # Mock logger to avoid conflicts
    @patch("xagent.core.planner.Planner")
    @patch("xagent.core.goal_engine.GoalEngine")
    def test_process_goal_not_found(self, mock_goal_engine_class, mock_planner_class, mock_logger):
        """Test processing non-existent goal."""
        # Setup mocks
        mock_goal_engine = MagicMock()
        mock_goal_engine_class.return_value = mock_goal_engine
        mock_goal_engine.get_goal.return_value = None

        # Execute task - expect ValueError (which will trigger retry)
        with pytest.raises(Exception):  # Either ValueError or Retry exception
            process_goal.apply(args=("nonexistent",)).get()

    @patch("xagent.core.planner.Planner")
    @patch("xagent.core.goal_engine.GoalEngine")
    def test_process_goal_no_sub_goals(self, mock_goal_engine_class, mock_planner_class):
        """Test processing goal with no sub-goals."""
        # Setup mocks
        mock_goal_engine = MagicMock()
        mock_goal_engine_class.return_value = mock_goal_engine

        mock_goal = MagicMock()
        mock_goal.status = "completed"
        mock_goal_engine.get_goal.return_value = mock_goal

        mock_planner = MagicMock()
        mock_planner_class.return_value = mock_planner
        mock_planner.create_plan.return_value = {}

        # Execute task
        result = process_goal(goal_id="goal-123")

        # Verify results
        assert result["status"] == "success"
        assert result["sub_goals_created"] == 0


class TestCleanupMemory:
    """Tests for cleanup_memory task."""

    def test_cleanup_memory_success(self):
        """Test successful memory cleanup."""
        # Execute task (placeholder implementation)
        result = cleanup_memory(max_age_hours=24, batch_size=100)

        # Verify results
        assert result["status"] == "success"
        assert "entries_removed" in result
        assert "goals_archived" in result

    def test_cleanup_memory_with_custom_params(self):
        """Test memory cleanup with custom parameters."""
        # Execute task
        result = cleanup_memory(max_age_hours=48, batch_size=50)

        # Verify results
        assert result["status"] == "success"

    @patch("xagent.memory.memory_layer.MemoryLayer")
    def test_cleanup_memory_error_handling(self, mock_memory_layer):
        """Test memory cleanup with error."""
        # Setup mock to raise error
        mock_memory_layer.side_effect = Exception("Cleanup failed")

        # Execute task - should handle error gracefully
        result = cleanup_memory()

        # Verify graceful handling
        assert result["status"] in ["success", "failure"]


def test_task_registration():
    """Test that all tasks are registered with Celery."""
    from xagent.tasks.queue import celery_app

    registered_tasks = celery_app.tasks.keys()

    assert "xagent.tasks.worker.execute_cognitive_loop" in registered_tasks
    assert "xagent.tasks.worker.execute_tool" in registered_tasks
    assert "xagent.tasks.worker.process_goal" in registered_tasks
    assert "xagent.tasks.worker.cleanup_memory" in registered_tasks


def test_task_retry_configuration():
    """Test that tasks have proper retry configuration."""
    assert execute_cognitive_loop.max_retries == 3
    assert execute_tool.max_retries == 2
    assert process_goal.max_retries == 3
    assert cleanup_memory.max_retries == 1
