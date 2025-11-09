"""Tests for cognitive loop."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from xagent.core.cognitive_loop import (
    CognitiveLoop,
    CognitiveState,
    LoopPhase,
)
from xagent.core.goal_engine import GoalEngine, Goal, GoalStatus, GoalMode


@pytest.fixture
def mock_goal_engine():
    """Create a mock goal engine."""
    engine = MagicMock(spec=GoalEngine)
    engine.get_active_goal = MagicMock(return_value=None)
    engine.get_goal = MagicMock(return_value=None)
    engine.list_goals = MagicMock(return_value=[])
    engine.get_next_goal = MagicMock(return_value=None)
    engine.set_active_goal = MagicMock()
    engine.check_goal_completion = MagicMock(return_value=False)
    engine.update_goal_status = MagicMock()
    return engine


@pytest.fixture
def mock_memory():
    """Create a mock memory layer."""
    memory = MagicMock()
    memory.get = AsyncMock(return_value=None)
    memory.store = AsyncMock()
    memory.save_short_term = AsyncMock()
    memory.save_medium_term = AsyncMock()
    return memory


@pytest.fixture
def mock_planner():
    """Create a mock planner."""
    planner = MagicMock()
    planner.create_plan = AsyncMock(return_value=None)
    return planner


@pytest.fixture
def mock_executor():
    """Create a mock executor."""
    executor = MagicMock()
    executor.execute = AsyncMock(return_value={"success": True})
    return executor


@pytest.fixture
def cognitive_loop(mock_goal_engine, mock_memory, mock_planner, mock_executor):
    """Create a cognitive loop instance."""
    return CognitiveLoop(
        goal_engine=mock_goal_engine,
        memory=mock_memory,
        planner=mock_planner,
        executor=mock_executor,
    )


class TestCognitiveLoopInitialization:
    """Tests for cognitive loop initialization."""

    def test_initialization(self, cognitive_loop):
        """Test cognitive loop initialization."""
        assert cognitive_loop.state == CognitiveState.IDLE
        assert cognitive_loop.current_phase == LoopPhase.PERCEPTION
        assert cognitive_loop.running is False
        assert cognitive_loop.iteration_count == 0
        assert cognitive_loop.perception_queue is not None

    def test_initialization_with_components(
        self, mock_goal_engine, mock_memory, mock_planner, mock_executor
    ):
        """Test that components are stored correctly."""
        loop = CognitiveLoop(
            goal_engine=mock_goal_engine,
            memory=mock_memory,
            planner=mock_planner,
            executor=mock_executor,
        )
        assert loop.goal_engine is mock_goal_engine
        assert loop.memory is mock_memory
        assert loop.planner is mock_planner
        assert loop.executor is mock_executor


class TestCognitiveLoopStates:
    """Tests for cognitive loop states."""

    def test_initial_state_idle(self, cognitive_loop):
        """Test initial state is IDLE."""
        assert cognitive_loop.state == CognitiveState.IDLE

    def test_phase_enum_values(self):
        """Test loop phase enum values."""
        assert LoopPhase.PERCEPTION.value == "perception"
        assert LoopPhase.INTERPRETATION.value == "interpretation"
        assert LoopPhase.PLANNING.value == "planning"
        assert LoopPhase.EXECUTION.value == "execution"
        assert LoopPhase.REFLECTION.value == "reflection"

    def test_state_enum_values(self):
        """Test cognitive state enum values."""
        assert CognitiveState.IDLE.value == "idle"
        assert CognitiveState.THINKING.value == "thinking"
        assert CognitiveState.ACTING.value == "acting"
        assert CognitiveState.REFLECTING.value == "reflecting"
        assert CognitiveState.STOPPED.value == "stopped"


class TestCognitiveLoopPerception:
    """Tests for perception phase."""

    @pytest.mark.asyncio
    async def test_add_perception(self, cognitive_loop):
        """Test adding perception data."""
        data = {"type": "command", "content": "test"}
        await cognitive_loop.add_perception(data)

        # Verify data is in queue
        assert not cognitive_loop.perception_queue.empty()
        retrieved = await cognitive_loop.perception_queue.get()
        assert retrieved == data

    @pytest.mark.asyncio
    async def test_add_multiple_perceptions(self, cognitive_loop):
        """Test adding multiple perceptions."""
        data1 = {"type": "command", "content": "first"}
        data2 = {"type": "event", "content": "second"}
        data3 = {"type": "message", "content": "third"}

        await cognitive_loop.add_perception(data1)
        await cognitive_loop.add_perception(data2)
        await cognitive_loop.add_perception(data3)

        assert cognitive_loop.perception_queue.qsize() == 3

    @pytest.mark.asyncio
    async def test_perceive_empty_queue(self, cognitive_loop):
        """Test perception with empty queue."""
        perception = await cognitive_loop._perceive()

        assert "timestamp" in perception
        assert "inputs" in perception
        assert perception["inputs"] == []
        assert "active_goal" in perception

    @pytest.mark.asyncio
    async def test_perceive_with_data(self, cognitive_loop):
        """Test perception with data in queue."""
        data = {"type": "command", "content": "test"}
        await cognitive_loop.add_perception(data)

        perception = await cognitive_loop._perceive()

        assert len(perception["inputs"]) == 1
        assert perception["inputs"][0] == data

    @pytest.mark.asyncio
    async def test_perceive_with_active_goal(self, cognitive_loop, mock_goal_engine):
        """Test perception with active goal."""
        goal = Goal(
            id="test-goal",
            description="Test goal",
            status=GoalStatus.IN_PROGRESS,
        )
        mock_goal_engine.get_active_goal.return_value = goal

        perception = await cognitive_loop._perceive()

        assert perception["active_goal"] is not None
        assert perception["active_goal"]["id"] == "test-goal"


class TestCognitiveLoopInterpretation:
    """Tests for interpretation phase."""

    @pytest.mark.asyncio
    async def test_interpret_basic(self, cognitive_loop):
        """Test basic interpretation."""
        perception = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "inputs": [],
            "active_goal": None,
        }

        context = await cognitive_loop._interpret(perception)

        assert "timestamp" in context
        assert "active_goal" in context
        assert "inputs" in context
        assert "memory_context" in context

    @pytest.mark.asyncio
    async def test_interpret_with_active_goal(self, cognitive_loop, mock_memory):
        """Test interpretation with active goal."""
        perception = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "inputs": [],
            "active_goal": {"id": "test-goal", "description": "Test"},
        }

        mock_memory.get.return_value = [{"action": "think", "result": "success"}]

        context = await cognitive_loop._interpret(perception)

        assert context["active_goal"]["id"] == "test-goal"
        # Memory should be queried
        mock_memory.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_interpret_command_input(self, cognitive_loop):
        """Test interpretation with command input."""
        perception = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "inputs": [{"type": "command", "content": "do something"}],
            "active_goal": None,
        }

        context = await cognitive_loop._interpret(perception)

        assert len(context["inputs"]) == 1
        assert context.get("priority") == "high"


class TestCognitiveLoopPlanning:
    """Tests for planning phase."""

    @pytest.mark.asyncio
    async def test_plan_no_active_goal(self, cognitive_loop, mock_planner, mock_goal_engine):
        """Test planning without active goal."""
        context = {"active_goal": None}
        # Ensure no next goal either
        mock_goal_engine.get_next_goal.return_value = None

        plan = await cognitive_loop._plan(context)

        # Should return None when no goal
        assert plan is None
        mock_planner.create_plan.assert_not_called()

    @pytest.mark.asyncio
    async def test_plan_with_active_goal(self, cognitive_loop, mock_planner):
        """Test planning with active goal."""
        mock_plan = {"steps": ["step1", "step2"]}
        mock_planner.create_plan.return_value = mock_plan

        context = {
            "active_goal": {"id": "test-goal", "description": "Test goal"},
            "memory_context": {},
        }

        plan = await cognitive_loop._plan(context)

        assert plan == mock_plan
        mock_planner.create_plan.assert_called_once()


class TestCognitiveLoopExecution:
    """Tests for execution phase."""

    @pytest.mark.asyncio
    async def test_execute_plan(self, cognitive_loop, mock_executor):
        """Test executing a plan."""
        plan = {"actions": [{"type": "think", "content": "test"}]}
        mock_executor.execute.return_value = {"success": True, "result": "done"}

        result = await cognitive_loop._execute(plan)

        assert result["success"] is True
        mock_executor.execute.assert_called_once_with(plan)

    @pytest.mark.asyncio
    async def test_execute_empty_plan(self, cognitive_loop, mock_executor):
        """Test executing empty plan."""
        plan = {}

        result = await cognitive_loop._execute(plan)

        mock_executor.execute.assert_called_once()


class TestCognitiveLoopReflection:
    """Tests for reflection phase."""

    @pytest.mark.asyncio
    async def test_reflect_success(self, cognitive_loop, mock_memory):
        """Test reflection on successful execution."""
        result = {"success": True, "result": "completed task"}

        await cognitive_loop._reflect(result)

        # Should store reflection in memory
        mock_memory.save_short_term.assert_called_once()

    @pytest.mark.asyncio
    async def test_reflect_failure(self, cognitive_loop, mock_memory):
        """Test reflection on failed execution."""
        result = {"success": False, "error": "something went wrong"}

        await cognitive_loop._reflect(result)

        # Should still store reflection
        mock_memory.save_short_term.assert_called_once()


class TestCognitiveLoopControl:
    """Tests for loop control (start/stop)."""

    @pytest.mark.asyncio
    async def test_start_loop(self, cognitive_loop):
        """Test starting the loop."""
        # Mock the _loop method to avoid infinite loop
        cognitive_loop._loop = AsyncMock()

        await cognitive_loop.start()

        assert cognitive_loop.running is True
        assert cognitive_loop.state == CognitiveState.THINKING
        cognitive_loop._loop.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_already_running(self, cognitive_loop):
        """Test starting loop when already running."""
        cognitive_loop.running = True
        cognitive_loop._loop = AsyncMock()

        await cognitive_loop.start()

        # Should not call _loop again
        cognitive_loop._loop.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_loop(self, cognitive_loop):
        """Test stopping the loop."""
        cognitive_loop.running = True

        await cognitive_loop.stop()

        assert cognitive_loop.running is False
        assert cognitive_loop.state == CognitiveState.STOPPED

    @pytest.mark.asyncio
    async def test_loop_stops_at_max_iterations(self, cognitive_loop):
        """Test loop stops at max iterations."""
        cognitive_loop.max_iterations = 2
        cognitive_loop._perceive = AsyncMock(
            return_value={"timestamp": "", "inputs": [], "active_goal": None}
        )
        cognitive_loop._interpret = AsyncMock(return_value={})
        cognitive_loop._plan = AsyncMock(return_value=None)

        cognitive_loop.running = True
        await cognitive_loop._loop()

        assert cognitive_loop.iteration_count == 2

    @pytest.mark.asyncio
    async def test_loop_handles_errors(self, cognitive_loop):
        """Test loop handles errors gracefully."""
        cognitive_loop.max_iterations = 2
        cognitive_loop._perceive = AsyncMock(side_effect=Exception("Test error"))

        cognitive_loop.running = True
        await cognitive_loop._loop()

        # Should complete without crashing
        assert cognitive_loop.iteration_count == 2


class TestCognitiveLoopIntegration:
    """Integration tests for full loop cycle."""

    @pytest.mark.asyncio
    async def test_full_cycle_no_goal(
        self, cognitive_loop, mock_goal_engine, mock_planner
    ):
        """Test full cycle without active goal."""
        cognitive_loop.max_iterations = 1
        mock_goal_engine.get_active_goal.return_value = None

        cognitive_loop.running = True
        await cognitive_loop._loop()

        # Should complete one iteration
        assert cognitive_loop.iteration_count == 1
        # Planner should not be called without goal
        mock_planner.create_plan.assert_not_called()

    @pytest.mark.asyncio
    async def test_full_cycle_with_goal_and_plan(
        self,
        cognitive_loop,
        mock_goal_engine,
        mock_planner,
        mock_executor,
        mock_memory,
    ):
        """Test full cycle with goal and plan."""
        cognitive_loop.max_iterations = 1

        # Setup goal
        goal = Goal(
            id="test-goal",
            description="Test goal",
            status=GoalStatus.IN_PROGRESS,
        )
        mock_goal_engine.get_active_goal.return_value = goal

        # Setup plan
        mock_plan = {"actions": [{"type": "think"}]}
        mock_planner.create_plan.return_value = mock_plan

        # Setup execution result
        mock_executor.execute.return_value = {"success": True}

        cognitive_loop.running = True
        await cognitive_loop._loop()

        # Verify all phases executed
        assert cognitive_loop.iteration_count == 1
        mock_planner.create_plan.assert_called_once()
        mock_executor.execute.assert_called_once()
        mock_memory.save_short_term.assert_called_once()

    @pytest.mark.asyncio
    async def test_loop_with_perception_input(self, cognitive_loop, mock_goal_engine):
        """Test loop with perception input."""
        cognitive_loop.max_iterations = 1
        mock_goal_engine.get_active_goal.return_value = None

        # Add perception before starting
        await cognitive_loop.add_perception(
            {"type": "command", "content": "test command"}
        )

        cognitive_loop.running = True
        await cognitive_loop._loop()

        assert cognitive_loop.iteration_count == 1

    @pytest.mark.asyncio
    async def test_loop_state_transitions(
        self, cognitive_loop, mock_goal_engine, mock_planner
    ):
        """Test state transitions during loop."""
        cognitive_loop.max_iterations = 1

        # Setup goal and plan to trigger execution
        goal = Goal(
            id="test-goal", description="Test", status=GoalStatus.IN_PROGRESS
        )
        mock_goal_engine.get_active_goal.return_value = goal
        mock_planner.create_plan.return_value = {"actions": []}

        initial_state = cognitive_loop.state
        assert initial_state == CognitiveState.IDLE

        cognitive_loop.running = True
        await cognitive_loop._loop()

        # After loop, should have transitioned through states
        assert cognitive_loop.iteration_count == 1


class TestCognitiveLoopPhases:
    """Tests for individual phases."""

    @pytest.mark.asyncio
    async def test_all_phases_executed_in_order(self, cognitive_loop):
        """Test that all phases execute in correct order."""
        cognitive_loop.max_iterations = 1

        phases_executed = []

        async def track_phase(phase_name):
            phases_executed.append(phase_name)

        # Mock phase methods to track execution
        async def mock_perceive():
            await track_phase("perception")
            return {"timestamp": "", "inputs": [], "active_goal": None}

        async def mock_interpret(perception):
            await track_phase("interpretation")
            return {}

        async def mock_plan(context):
            await track_phase("planning")
            return None

        cognitive_loop._perceive = mock_perceive
        cognitive_loop._interpret = mock_interpret
        cognitive_loop._plan = mock_plan

        cognitive_loop.running = True
        await cognitive_loop._loop()

        assert phases_executed == ["perception", "interpretation", "planning"]

    @pytest.mark.asyncio
    async def test_execution_only_with_plan(
        self, cognitive_loop, mock_planner, mock_executor, mock_goal_engine
    ):
        """Test execution only happens when there's a plan."""
        cognitive_loop.max_iterations = 1

        # No active goal and no next goal, so no plan
        mock_goal_engine.get_active_goal.return_value = None
        mock_goal_engine.get_next_goal.return_value = None
        mock_planner.create_plan.return_value = None

        cognitive_loop.running = True
        await cognitive_loop._loop()

        # Executor should not be called
        mock_executor.execute.assert_not_called()
