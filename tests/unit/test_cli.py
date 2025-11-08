"""Unit tests for X-Agent CLI."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock

import pytest
from typer.testing import CliRunner

from xagent.cli.main import app, initialize_agent, get_agent
from xagent.core.agent import XAgent
from xagent.core.goal_engine import Goal, GoalMode, GoalStatus


runner = CliRunner()


class TestCLICommands:
    """Test CLI commands."""

    def test_version_command(self):
        """Test version command."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "X-Agent" in result.stdout
        assert "v0.1.0" in result.stdout
        assert "Production Ready" in result.stdout

    @patch("xagent.cli.main.initialize_agent")
    @patch("xagent.cli.main._interactive_loop")
    def test_interactive_command(self, mock_loop, mock_init):
        """Test interactive command launches interactive mode."""
        # Mock async functions
        mock_init.return_value = asyncio.Future()
        mock_init.return_value.set_result(Mock(spec=XAgent))

        mock_loop.return_value = asyncio.Future()
        mock_loop.return_value.set_result(None)

        result = runner.invoke(app, ["interactive"])

        # Check that interactive mode was started
        assert result.exit_code == 0
        mock_init.assert_called_once()
        mock_loop.assert_called_once()

    @patch("xagent.cli.main.XAgent")
    @patch("xagent.cli.main.configure_logging")
    def test_start_command(self, mock_logging, mock_xagent_class):
        """Test start command."""
        # Create a mock agent instance
        mock_agent = AsyncMock(spec=XAgent)
        mock_agent.initialize = AsyncMock()
        mock_agent.start = AsyncMock()

        # Make XAgent constructor return our mock
        mock_xagent_class.return_value = mock_agent

        result = runner.invoke(app, ["start", "Test goal"])

        assert result.exit_code == 0
        assert "started" in result.stdout.lower()

    @patch("xagent.cli.main.XAgent")
    @patch("xagent.cli.main.configure_logging")
    def test_start_command_with_background_flag(self, mock_logging, mock_xagent_class):
        """Test start command with background flag."""
        # Create a mock agent instance
        mock_agent = AsyncMock(spec=XAgent)
        mock_agent.initialize = AsyncMock()
        mock_agent.start = AsyncMock()

        # Make XAgent constructor return our mock
        mock_xagent_class.return_value = mock_agent

        result = runner.invoke(app, ["start", "--background", "Test goal"])

        assert result.exit_code == 0
        assert "background" in result.stdout.lower()

    def test_status_command(self):
        """Test status command."""
        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        # Status should show a message about needing to be initialized
        assert "agent" in result.stdout.lower()


class TestGetAgent:
    """Test get_agent function."""

    def test_get_agent_not_initialized(self):
        """Test get_agent raises error when agent not initialized."""
        import xagent.cli.main

        xagent.cli.main._agent = None

        with pytest.raises(Exception) as exc_info:
            get_agent()

        assert "not initialized" in str(exc_info.value).lower()

    def test_get_agent_initialized(self):
        """Test get_agent returns agent when initialized."""
        import xagent.cli.main

        mock_agent = Mock(spec=XAgent)
        xagent.cli.main._agent = mock_agent

        agent = get_agent()
        assert agent is mock_agent

        # Cleanup
        xagent.cli.main._agent = None


class TestInteractiveCommands:
    """Test interactive mode commands."""

    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent for testing."""
        agent = AsyncMock(spec=XAgent)
        agent.goal_engine = Mock()
        agent.start = AsyncMock()
        agent.stop = AsyncMock()
        agent.send_command = AsyncMock()
        agent.send_feedback = AsyncMock()
        agent.get_status = AsyncMock(
            return_value={
                "initialized": True,
                "running": True,
                "state": "idle",
                "iteration_count": 0,
                "goals_summary": {
                    "total": 1,
                    "pending": 0,
                    "in_progress": 1,
                    "completed": 0,
                },
                "active_goal": {
                    "id": "test-goal-1",
                    "description": "Test goal",
                    "status": "in_progress",
                    "mode": "goal_oriented",
                },
                "performance": {
                    "total_actions": 5,
                    "success_rate": 0.8,
                },
            }
        )
        return agent

    @pytest.mark.asyncio
    async def test_cmd_start(self, mock_agent):
        """Test start command in interactive mode."""
        from xagent.cli.main import _cmd_start
        import xagent.cli.main

        xagent.cli.main._agent = mock_agent

        await _cmd_start("Test goal")

        mock_agent.start.assert_called_once_with(initial_goal="Test goal")

        # Cleanup
        xagent.cli.main._agent = None

    @pytest.mark.asyncio
    async def test_cmd_stop(self, mock_agent):
        """Test stop command in interactive mode."""
        from xagent.cli.main import _cmd_stop
        import xagent.cli.main

        xagent.cli.main._agent = mock_agent

        await _cmd_stop()

        mock_agent.stop.assert_called_once()

        # Cleanup
        xagent.cli.main._agent = None

    @pytest.mark.asyncio
    async def test_cmd_status(self, mock_agent):
        """Test status command in interactive mode."""
        from xagent.cli.main import _cmd_status
        import xagent.cli.main

        xagent.cli.main._agent = mock_agent

        # Should not raise any exceptions
        await _cmd_status()

        mock_agent.get_status.assert_called_once()

        # Cleanup
        xagent.cli.main._agent = None

    @pytest.mark.asyncio
    async def test_cmd_goal(self, mock_agent):
        """Test goal creation in interactive mode."""
        from xagent.cli.main import _cmd_goal
        import xagent.cli.main

        xagent.cli.main._agent = mock_agent

        # Mock goal creation
        mock_goal = Mock(spec=Goal)
        mock_goal.id = "test-goal-1"
        mock_goal.description = "Test goal"
        mock_agent.goal_engine.create_goal = Mock(return_value=mock_goal)

        await _cmd_goal("Test goal description")

        mock_agent.goal_engine.create_goal.assert_called_once()

        # Cleanup
        xagent.cli.main._agent = None

    @pytest.mark.asyncio
    async def test_cmd_list_goals(self, mock_agent):
        """Test listing goals in interactive mode."""
        from xagent.cli.main import _cmd_list_goals
        import xagent.cli.main

        xagent.cli.main._agent = mock_agent

        # Mock goals
        mock_goal = Mock(spec=Goal)
        mock_goal.id = "test-goal-1"
        mock_goal.description = "Test goal"
        mock_goal.status = GoalStatus.IN_PROGRESS
        mock_goal.mode = GoalMode.GOAL_ORIENTED
        mock_goal.priority = 5

        mock_agent.goal_engine.list_goals = Mock(return_value=[mock_goal])

        # Should not raise any exceptions
        await _cmd_list_goals()

        mock_agent.goal_engine.list_goals.assert_called_once()

        # Cleanup
        xagent.cli.main._agent = None

    @pytest.mark.asyncio
    async def test_cmd_send_command(self, mock_agent):
        """Test sending command in interactive mode."""
        from xagent.cli.main import _cmd_send_command
        import xagent.cli.main

        xagent.cli.main._agent = mock_agent

        await _cmd_send_command("Test command")

        mock_agent.send_command.assert_called_once_with("Test command")

        # Cleanup
        xagent.cli.main._agent = None

    @pytest.mark.asyncio
    async def test_cmd_send_feedback(self, mock_agent):
        """Test sending feedback in interactive mode."""
        from xagent.cli.main import _cmd_send_feedback
        import xagent.cli.main

        xagent.cli.main._agent = mock_agent

        await _cmd_send_feedback("Test feedback")

        mock_agent.send_feedback.assert_called_once_with("Test feedback")

        # Cleanup
        xagent.cli.main._agent = None


class TestCLIHelp:
    """Test CLI help text."""

    def test_main_help(self):
        """Test main help command."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "X-Agent" in result.stdout
        assert "Autonomous AI Agent" in result.stdout

    def test_interactive_help(self):
        """Test interactive command help."""
        result = runner.invoke(app, ["interactive", "--help"])
        assert result.exit_code == 0
        assert "interactive" in result.stdout.lower()

    def test_start_help(self):
        """Test start command help."""
        result = runner.invoke(app, ["start", "--help"])
        assert result.exit_code == 0
        assert "start" in result.stdout.lower()
        assert "goal" in result.stdout.lower()

    def test_status_help(self):
        """Test status command help."""
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0
        assert "status" in result.stdout.lower()

    def test_version_help(self):
        """Test version command help."""
        result = runner.invoke(app, ["version", "--help"])
        assert result.exit_code == 0
        assert "version" in result.stdout.lower()


class TestCLICompletion:
    """Test shell completion support."""

    def test_completion_install(self):
        """Test that completion installation works."""
        result = runner.invoke(app, ["--install-completion"])
        # Exit code 0 or 1 is acceptable (depends on shell)
        assert result.exit_code in [0, 1]

    def test_completion_show(self):
        """Test that completion can be shown."""
        result = runner.invoke(app, ["--show-completion"])
        # Should output completion script
        assert result.exit_code == 0
