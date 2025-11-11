"""Tests for checkpoint and recovery functionality."""

import asyncio
import json
import pickle
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from xagent.core.cognitive_loop import CognitiveLoop, CognitiveState, LoopPhase
from xagent.core.executor import Executor
from xagent.core.goal_engine import GoalEngine
from xagent.core.planner import Planner
from xagent.memory.memory_layer import MemoryLayer


@pytest.fixture
def mock_memory():
    """Create a mock memory layer."""
    memory = Mock(spec=MemoryLayer)
    memory.get = AsyncMock(return_value=None)
    memory.save_short_term = AsyncMock()
    memory.save_medium_term = AsyncMock()
    return memory


@pytest.fixture
def mock_goal_engine():
    """Create a mock goal engine."""
    engine = Mock(spec=GoalEngine)
    engine.get_active_goal = Mock(return_value=None)
    engine.get_next_goal = Mock(return_value=None)
    engine.active_goal_id = None
    engine.set_active_goal = Mock()
    return engine


@pytest.fixture
def mock_planner():
    """Create a mock planner."""
    planner = Mock(spec=Planner)
    planner.create_plan = AsyncMock(return_value=None)
    return planner


@pytest.fixture
def mock_executor():
    """Create a mock executor."""
    executor = Mock(spec=Executor)
    executor.execute = AsyncMock(
        return_value={
            "success": True,
            "output": {"message": "test"},
            "error": None,
        }
    )
    return executor


@pytest.fixture
def cognitive_loop(mock_goal_engine, mock_memory, mock_planner, mock_executor, tmp_path):
    """Create a cognitive loop with checkpoint configuration."""
    loop = CognitiveLoop(
        goal_engine=mock_goal_engine,
        memory=mock_memory,
        planner=mock_planner,
        executor=mock_executor,
    )
    # Use tmp_path for checkpoints
    loop.checkpoint_dir = tmp_path / "checkpoints"
    loop.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    return loop


class TestCheckpointFunctionality:
    """Test checkpoint save and restore functionality."""

    def test_checkpoint_configuration(self, cognitive_loop):
        """Test that checkpoint is properly configured."""
        assert cognitive_loop.checkpoint_enabled is True
        assert cognitive_loop.checkpoint_interval == 10
        assert cognitive_loop.checkpoint_dir.exists()
        assert cognitive_loop.last_checkpoint_iteration == 0

    def test_get_checkpoint_state(self, cognitive_loop):
        """Test getting checkpoint state."""
        # Set some state
        cognitive_loop.iteration_count = 42
        cognitive_loop.state = CognitiveState.THINKING
        cognitive_loop.current_phase = LoopPhase.PLANNING
        cognitive_loop.start_time = 1234567890.0
        cognitive_loop.task_results = [True, False, True]

        # Get checkpoint state
        state = cognitive_loop._get_checkpoint_state()

        # Verify state
        assert state["iteration_count"] == 42
        assert state["state"] == "thinking"
        assert state["current_phase"] == "planning"
        assert state["start_time"] == 1234567890.0
        assert state["task_results"] == [True, False, True]
        assert "timestamp" in state

    @pytest.mark.asyncio
    async def test_save_checkpoint(self, cognitive_loop):
        """Test saving checkpoint to file."""
        # Set some state
        cognitive_loop.iteration_count = 10
        cognitive_loop.state = CognitiveState.ACTING
        cognitive_loop.task_results = [True, True, False]

        # Save checkpoint
        await cognitive_loop.save_checkpoint()

        # Verify files were created
        json_path = cognitive_loop.checkpoint_dir / "checkpoint.json"
        pickle_path = cognitive_loop.checkpoint_dir / "checkpoint.pkl"

        assert json_path.exists()
        assert pickle_path.exists()

        # Verify JSON content
        with open(json_path, "r") as f:
            data = json.load(f)
        
        assert data["iteration_count"] == 10
        assert data["state"] == "acting"
        assert data["task_results"] == [True, True, False]

        # Verify last checkpoint iteration was updated
        assert cognitive_loop.last_checkpoint_iteration == 10

    @pytest.mark.asyncio
    async def test_load_checkpoint(self, cognitive_loop):
        """Test loading checkpoint from file."""
        # Save a checkpoint first
        cognitive_loop.iteration_count = 25
        cognitive_loop.state = CognitiveState.REFLECTING
        cognitive_loop.current_phase = LoopPhase.REFLECTION
        cognitive_loop.start_time = 9876543210.0
        cognitive_loop.task_results = [True, False, True, True]
        await cognitive_loop.save_checkpoint()

        # Create a new loop instance
        new_loop = CognitiveLoop(
            goal_engine=cognitive_loop.goal_engine,
            memory=cognitive_loop.memory,
            planner=cognitive_loop.planner,
            executor=cognitive_loop.executor,
        )
        new_loop.checkpoint_dir = cognitive_loop.checkpoint_dir

        # Load checkpoint
        loaded = await new_loop.load_checkpoint()

        # Verify checkpoint was loaded
        assert loaded is True
        assert new_loop.iteration_count == 25
        assert new_loop.state == CognitiveState.REFLECTING
        assert new_loop.current_phase == LoopPhase.REFLECTION
        assert new_loop.start_time == 9876543210.0
        assert new_loop.task_results == [True, False, True, True]

    @pytest.mark.asyncio
    async def test_load_checkpoint_no_file(self, cognitive_loop):
        """Test loading checkpoint when no file exists."""
        # Ensure no checkpoint file exists
        json_path = cognitive_loop.checkpoint_dir / "checkpoint.json"
        pickle_path = cognitive_loop.checkpoint_dir / "checkpoint.pkl"
        
        if json_path.exists():
            json_path.unlink()
        if pickle_path.exists():
            pickle_path.unlink()

        # Try to load checkpoint
        loaded = await cognitive_loop.load_checkpoint()

        # Verify nothing was loaded
        assert loaded is False
        assert cognitive_loop.iteration_count == 0

    def test_should_checkpoint_enabled(self, cognitive_loop):
        """Test should_checkpoint logic when enabled."""
        cognitive_loop.checkpoint_enabled = True
        cognitive_loop.checkpoint_interval = 10
        cognitive_loop.last_checkpoint_iteration = 0

        # Should not checkpoint before interval
        cognitive_loop.iteration_count = 5
        assert cognitive_loop.should_checkpoint() is False

        # Should checkpoint at interval
        cognitive_loop.iteration_count = 10
        assert cognitive_loop.should_checkpoint() is True

        # Should checkpoint after interval
        cognitive_loop.iteration_count = 15
        assert cognitive_loop.should_checkpoint() is True

    def test_should_checkpoint_disabled(self, cognitive_loop):
        """Test should_checkpoint returns False when disabled."""
        cognitive_loop.checkpoint_enabled = False
        cognitive_loop.iteration_count = 100

        assert cognitive_loop.should_checkpoint() is False

    @pytest.mark.asyncio
    async def test_save_checkpoint_disabled(self, cognitive_loop):
        """Test that checkpoint is not saved when disabled."""
        cognitive_loop.checkpoint_enabled = False
        cognitive_loop.iteration_count = 10

        # Try to save checkpoint
        await cognitive_loop.save_checkpoint()

        # Verify no files were created
        json_path = cognitive_loop.checkpoint_dir / "checkpoint.json"
        pickle_path = cognitive_loop.checkpoint_dir / "checkpoint.pkl"

        assert not json_path.exists()
        assert not pickle_path.exists()

    @pytest.mark.asyncio
    async def test_checkpoint_with_active_goal(self, cognitive_loop, mock_goal_engine):
        """Test checkpoint saves and restores active goal."""
        # Set active goal
        mock_goal_engine.active_goal_id = "goal-123"
        cognitive_loop.iteration_count = 10

        # Save checkpoint
        await cognitive_loop.save_checkpoint()

        # Create new loop and load
        new_loop = CognitiveLoop(
            goal_engine=mock_goal_engine,
            memory=cognitive_loop.memory,
            planner=cognitive_loop.planner,
            executor=cognitive_loop.executor,
        )
        new_loop.checkpoint_dir = cognitive_loop.checkpoint_dir

        # Load checkpoint
        loaded = await new_loop.load_checkpoint()

        # Verify active goal was restored
        assert loaded is True
        mock_goal_engine.set_active_goal.assert_called_once_with("goal-123")

    @pytest.mark.asyncio
    async def test_checkpoint_integration_with_loop(
        self, cognitive_loop, mock_planner, mock_executor
    ):
        """Test checkpoint automatically saves during loop execution."""
        # Configure for fast checkpointing
        cognitive_loop.checkpoint_interval = 2
        cognitive_loop.max_iterations = 5

        # Configure planner to return plans
        mock_planner.create_plan = AsyncMock(
            return_value={
                "type": "think",
                "action": "analyze",
                "parameters": {},
            }
        )

        # Run loop
        loop_task = asyncio.create_task(cognitive_loop.start(resume_from_checkpoint=False))
        await asyncio.sleep(1.5)
        await cognitive_loop.stop()

        try:
            await asyncio.wait_for(loop_task, timeout=2.0)
        except asyncio.TimeoutError:
            pass

        # Verify checkpoint was created
        pickle_path = cognitive_loop.checkpoint_dir / "checkpoint.pkl"
        assert pickle_path.exists()

        # Verify last checkpoint was updated
        assert cognitive_loop.last_checkpoint_iteration > 0

    @pytest.mark.asyncio
    async def test_resume_from_checkpoint(
        self, cognitive_loop, mock_planner, mock_executor, mock_goal_engine
    ):
        """Test resuming from checkpoint."""
        # Run loop to create checkpoint
        cognitive_loop.checkpoint_interval = 2
        cognitive_loop.max_iterations = 5

        mock_planner.create_plan = AsyncMock(
            return_value={
                "type": "think",
                "action": "analyze",
                "parameters": {},
            }
        )

        # First run
        loop_task = asyncio.create_task(cognitive_loop.start(resume_from_checkpoint=False))
        await asyncio.sleep(1.0)
        await cognitive_loop.stop()

        try:
            await asyncio.wait_for(loop_task, timeout=2.0)
        except asyncio.TimeoutError:
            pass

        # Save the iteration count
        first_run_iterations = cognitive_loop.iteration_count
        assert first_run_iterations > 0

        # Create new loop instance
        new_loop = CognitiveLoop(
            goal_engine=mock_goal_engine,
            memory=cognitive_loop.memory,
            planner=mock_planner,
            executor=mock_executor,
        )
        new_loop.checkpoint_dir = cognitive_loop.checkpoint_dir
        new_loop.max_iterations = 10

        # Resume from checkpoint
        loop_task = asyncio.create_task(new_loop.start(resume_from_checkpoint=True))
        await asyncio.sleep(0.5)
        await new_loop.stop()

        try:
            await asyncio.wait_for(loop_task, timeout=2.0)
        except asyncio.TimeoutError:
            pass

        # Verify it resumed from checkpoint (iteration count should be >= first run)
        # Note: might run additional iterations
        assert new_loop.iteration_count >= first_run_iterations


class TestCheckpointErrorHandling:
    """Test error handling in checkpoint functionality."""

    @pytest.mark.asyncio
    async def test_save_checkpoint_with_error(self, cognitive_loop, monkeypatch):
        """Test checkpoint save handles errors gracefully."""
        # Make pickle.dump raise an error
        def mock_dump(*args, **kwargs):
            raise Exception("Simulated pickle error")

        monkeypatch.setattr(pickle, "dump", mock_dump)

        # Should not raise exception
        await cognitive_loop.save_checkpoint()

        # Loop should continue functioning
        assert cognitive_loop.iteration_count == 0

    @pytest.mark.asyncio
    async def test_load_checkpoint_with_corrupted_file(self, cognitive_loop):
        """Test loading from corrupted checkpoint file."""
        # Create a corrupted checkpoint file
        pickle_path = cognitive_loop.checkpoint_dir / "checkpoint.pkl"
        with open(pickle_path, "wb") as f:
            f.write(b"corrupted data")

        # Should handle error gracefully
        loaded = await cognitive_loop.load_checkpoint()
        assert loaded is False

    @pytest.mark.asyncio
    async def test_checkpoint_dir_creation(self, tmp_path):
        """Test that checkpoint directory is created if it doesn't exist."""
        # Create loop with non-existent checkpoint dir
        mock_goal_engine = Mock(spec=GoalEngine)
        mock_goal_engine.get_active_goal = Mock(return_value=None)
        mock_memory = Mock(spec=MemoryLayer)
        mock_planner = Mock(spec=Planner)
        mock_executor = Mock(spec=Executor)

        loop = CognitiveLoop(
            goal_engine=mock_goal_engine,
            memory=mock_memory,
            planner=mock_planner,
            executor=mock_executor,
        )

        # Set to non-existent directory
        loop.checkpoint_dir = tmp_path / "new_checkpoint_dir"

        # Save checkpoint should create directory
        await loop.save_checkpoint()

        # Verify directory was created
        assert loop.checkpoint_dir.exists()
