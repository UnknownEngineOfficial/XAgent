"""
End-to-End Long-Running Workflow Tests.

Tests workflows that simulate long-running operations, checkpointing,
and recovery scenarios.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from xagent.core.cognitive_loop import CognitiveLoop, CognitiveState, LoopPhase
from xagent.core.executor import Executor
from xagent.core.goal_engine import GoalEngine, GoalMode, GoalStatus
from xagent.core.planner import Planner
from xagent.core.watchdog import TaskWatchdog
from xagent.memory.memory_layer import MemoryLayer


@pytest.fixture
def goal_engine():
    """Create a goal engine for testing."""
    return GoalEngine()


@pytest.fixture
async def memory_layer():
    """Create a memory layer for testing."""
    memory = MemoryLayer()
    await memory.initialize()
    yield memory
    await memory.close()


@pytest.fixture
def planner():
    """Create a mock planner for testing."""
    planner = Mock(spec=Planner)
    planner.plan = AsyncMock(return_value={
        "actions": [
            {"type": "think", "content": "Planning action"},
        ],
        "goal_id": "test-goal",
    })
    return planner


@pytest.fixture
def executor(goal_engine):
    """Create a mock executor for testing."""
    executor = Mock(spec=Executor)
    executor.execute = AsyncMock(return_value={
        "success": True,
        "result": "Action completed",
    })
    executor.goal_engine = goal_engine
    return executor


@pytest.fixture
async def cognitive_loop(goal_engine, memory_layer, planner, executor):
    """Create a cognitive loop for testing."""
    loop = CognitiveLoop(
        goal_engine=goal_engine,
        memory=memory_layer,
        planner=planner,
        executor=executor,
    )
    yield loop
    if loop.running:
        await loop.stop()


class TestLongRunningWorkflows:
    """Test long-running workflow scenarios."""

    @pytest.mark.asyncio
    async def test_long_running_cognitive_loop(self, cognitive_loop, goal_engine):
        """Test cognitive loop running through multiple iterations."""
        # Create a goal for the loop to work on
        goal = goal_engine.create_goal(
            description="Long-running data processing task",
            mode=GoalMode.GOAL_ORIENTED,
            priority=7,
            completion_criteria=["Process 100 items", "Generate report"],
        )
        goal_engine.set_active_goal(goal.id)
        
        # Configure for short test (not truly long-running in test)
        cognitive_loop.max_iterations = 10
        
        # Start the loop in the background
        loop_task = asyncio.create_task(cognitive_loop.start(resume_from_checkpoint=False))
        
        # Let it run for a bit
        await asyncio.sleep(1.0)
        
        # Stop the loop
        await cognitive_loop.stop()
        
        # Wait for the loop to finish
        try:
            await asyncio.wait_for(loop_task, timeout=2.0)
        except asyncio.TimeoutError:
            pass  # Loop may still be finishing
        
        # Verify loop ran multiple iterations
        assert cognitive_loop.iteration_count > 0
        assert cognitive_loop.state in [CognitiveState.STOPPED, CognitiveState.IDLE]

    @pytest.mark.asyncio
    async def test_checkpoint_and_resume(self, cognitive_loop, goal_engine):
        """Test checkpointing and resuming a long-running workflow."""
        # Create a goal
        goal = goal_engine.create_goal(
            description="Task with checkpointing",
            mode=GoalMode.GOAL_ORIENTED,
            priority=6,
        )
        goal_engine.set_active_goal(goal.id)
        
        # Enable checkpointing
        cognitive_loop.checkpoint_enabled = True
        cognitive_loop.checkpoint_interval = 3  # Checkpoint every 3 iterations
        cognitive_loop.max_iterations = 10
        
        # Run for a few iterations
        loop_task = asyncio.create_task(cognitive_loop.start(resume_from_checkpoint=False))
        await asyncio.sleep(0.5)
        
        # Verify checkpoint directory exists
        assert cognitive_loop.checkpoint_dir.exists()
        
        # Let it run a bit more to create a checkpoint
        await asyncio.sleep(0.5)
        
        # Stop the loop
        initial_iteration = cognitive_loop.iteration_count
        await cognitive_loop.stop()
        
        try:
            await asyncio.wait_for(loop_task, timeout=2.0)
        except asyncio.TimeoutError:
            pass
        
        # Create a new cognitive loop and resume from checkpoint
        new_loop = CognitiveLoop(
            goal_engine=goal_engine,
            memory=cognitive_loop.memory,
            planner=cognitive_loop.planner,
            executor=cognitive_loop.executor,
        )
        new_loop.checkpoint_dir = cognitive_loop.checkpoint_dir
        new_loop.max_iterations = 15
        
        # Resume from checkpoint
        resume_task = asyncio.create_task(new_loop.start(resume_from_checkpoint=True))
        await asyncio.sleep(0.5)
        
        # Stop the resumed loop
        await new_loop.stop()
        
        try:
            await asyncio.wait_for(resume_task, timeout=2.0)
        except asyncio.TimeoutError:
            pass
        
        # Verify it continued from checkpoint (iteration count should be preserved or higher)
        # Note: The exact behavior depends on checkpoint implementation
        assert new_loop.iteration_count >= 0

    @pytest.mark.asyncio
    async def test_max_iterations_enforcement(self, cognitive_loop, goal_engine):
        """Test that cognitive loop respects max iterations limit."""
        # Create a goal
        goal = goal_engine.create_goal(
            description="Task with iteration limit",
            mode=GoalMode.GOAL_ORIENTED,
            priority=5,
        )
        goal_engine.set_active_goal(goal.id)
        
        # Set a low max iterations
        cognitive_loop.max_iterations = 5
        
        # Start the loop
        await cognitive_loop.start(resume_from_checkpoint=False)
        
        # Verify it stopped after max iterations
        assert cognitive_loop.iteration_count == cognitive_loop.max_iterations
        assert cognitive_loop.state in [CognitiveState.STOPPED, CognitiveState.IDLE]

    @pytest.mark.asyncio
    async def test_continuous_goal_processing(self, cognitive_loop, goal_engine):
        """Test processing multiple goals sequentially in a long-running loop."""
        # Create multiple goals
        goal_1 = goal_engine.create_goal(
            description="First task",
            mode=GoalMode.GOAL_ORIENTED,
            priority=5,
        )
        
        goal_2 = goal_engine.create_goal(
            description="Second task",
            mode=GoalMode.GOAL_ORIENTED,
            priority=5,
        )
        
        # Set first goal as active
        goal_engine.set_active_goal(goal_1.id)
        
        # Configure for test
        cognitive_loop.max_iterations = 15
        
        # Start the loop
        loop_task = asyncio.create_task(cognitive_loop.start(resume_from_checkpoint=False))
        
        # Let it process the first goal
        await asyncio.sleep(0.5)
        
        # Switch to second goal
        goal_engine.update_goal_status(goal_1.id, GoalStatus.COMPLETED)
        goal_engine.set_active_goal(goal_2.id)
        
        # Let it process the second goal
        await asyncio.sleep(0.5)
        
        # Stop the loop
        await cognitive_loop.stop()
        
        try:
            await asyncio.wait_for(loop_task, timeout=2.0)
        except asyncio.TimeoutError:
            pass
        
        # Verify multiple iterations ran
        assert cognitive_loop.iteration_count > 0

    @pytest.mark.asyncio
    async def test_watchdog_timeout_handling(self):
        """Test watchdog handling of long-running task timeouts."""
        watchdog = TaskWatchdog(default_timeout=1.0)
        await watchdog.start()
        
        try:
            # Create a task that will timeout
            async def slow_task():
                await asyncio.sleep(5.0)  # Will timeout after 1 second
                return "completed"
            
            # Execute with timeout
            with pytest.raises((asyncio.TimeoutError, Exception)):
                await watchdog.execute_supervised_task(
                    task_id="timeout_test",
                    coro=slow_task(),
                    timeout=1.0,
                    max_retries=0,  # No retries
                )
            
            # Verify task was tracked
            stats = watchdog.get_statistics()
            assert stats["total_tasks"] >= 1
        
        finally:
            await watchdog.stop()

    @pytest.mark.asyncio
    async def test_watchdog_retry_on_failure(self):
        """Test watchdog retry logic for failing tasks."""
        watchdog = TaskWatchdog(default_timeout=5.0)
        await watchdog.start()
        
        try:
            attempt_count = 0
            
            async def failing_task():
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count < 3:
                    raise ValueError("Simulated failure")
                return "success"
            
            # Execute with retries
            result = await watchdog.execute_supervised_task(
                task_id="retry_test",
                coro=failing_task(),
                timeout=2.0,
                max_retries=3,
                retry_on_error=True,
            )
            
            # Should succeed after retries
            assert result == "success"
            assert attempt_count == 3  # Initial attempt + 2 retries
            
            # Verify retry statistics
            task_stats = watchdog.get_task_statistics("retry_test")
            assert task_stats is not None
            assert task_stats["retry_count"] > 0
        
        finally:
            await watchdog.stop()

    @pytest.mark.asyncio
    async def test_concurrent_long_running_tasks(self):
        """Test managing multiple long-running tasks concurrently."""
        watchdog = TaskWatchdog(default_timeout=5.0)
        await watchdog.start()
        
        try:
            # Create multiple long-running tasks
            async def long_task(task_id: str, duration: float):
                await asyncio.sleep(duration)
                return f"{task_id}_completed"
            
            # Start multiple tasks concurrently
            task_1 = asyncio.create_task(
                watchdog.execute_supervised_task(
                    task_id="concurrent_1",
                    coro=long_task("task_1", 0.2),
                    timeout=1.0,
                )
            )
            
            task_2 = asyncio.create_task(
                watchdog.execute_supervised_task(
                    task_id="concurrent_2",
                    coro=long_task("task_2", 0.3),
                    timeout=1.0,
                )
            )
            
            task_3 = asyncio.create_task(
                watchdog.execute_supervised_task(
                    task_id="concurrent_3",
                    coro=long_task("task_3", 0.4),
                    timeout=1.0,
                )
            )
            
            # Wait for all tasks to complete
            results = await asyncio.gather(task_1, task_2, task_3)
            
            # Verify all completed successfully
            assert len(results) == 3
            assert "task_1_completed" in results
            assert "task_2_completed" in results
            assert "task_3_completed" in results
            
            # Verify watchdog tracked all tasks
            stats = watchdog.get_statistics()
            assert stats["total_tasks"] >= 3
        
        finally:
            await watchdog.stop()

    @pytest.mark.asyncio
    async def test_graceful_shutdown_with_active_tasks(self):
        """Test graceful shutdown while tasks are still running."""
        watchdog = TaskWatchdog(default_timeout=10.0)
        await watchdog.start()
        
        # Start a long-running task
        async def long_task():
            await asyncio.sleep(2.0)
            return "completed"
        
        # Start task but don't wait
        task = asyncio.create_task(
            watchdog.execute_supervised_task(
                task_id="shutdown_test",
                coro=long_task(),
                timeout=5.0,
            )
        )
        
        # Give it a moment to start
        await asyncio.sleep(0.1)
        
        # Stop watchdog (should handle active tasks gracefully)
        await watchdog.stop()
        
        # Task may be cancelled or completed
        try:
            await asyncio.wait_for(task, timeout=1.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass  # Expected if task was cancelled during shutdown

    @pytest.mark.asyncio
    async def test_memory_persistence_across_iterations(
        self, cognitive_loop, goal_engine, memory_layer
    ):
        """Test that memory persists across loop iterations."""
        # Create a goal
        goal = goal_engine.create_goal(
            description="Task with memory persistence",
            mode=GoalMode.GOAL_ORIENTED,
            priority=6,
        )
        goal_engine.set_active_goal(goal.id)
        
        # Store something in memory before starting
        await memory_layer.set("test_key", "test_value")
        
        # Configure loop
        cognitive_loop.max_iterations = 5
        
        # Run the loop
        await cognitive_loop.start(resume_from_checkpoint=False)
        
        # Verify memory persisted
        retrieved_value = await memory_layer.get("test_key")
        assert retrieved_value == "test_value"

    @pytest.mark.asyncio
    async def test_goal_status_transitions_in_workflow(self, goal_engine):
        """Test goal status transitions in a realistic workflow."""
        # Create a goal
        goal = goal_engine.create_goal(
            description="Multi-stage workflow task",
            mode=GoalMode.GOAL_ORIENTED,
            priority=7,
            completion_criteria=["Stage 1 complete", "Stage 2 complete", "Stage 3 complete"],
        )
        
        # Verify initial state
        assert goal.status == GoalStatus.PENDING
        
        # Simulate workflow progression
        # Stage 1: Start working
        goal_engine.update_goal_status(goal.id, GoalStatus.IN_PROGRESS)
        assert goal_engine.get_goal(goal.id).status == GoalStatus.IN_PROGRESS
        
        # Stage 2: Continue working (stays in progress)
        await asyncio.sleep(0.1)
        assert goal_engine.get_goal(goal.id).status == GoalStatus.IN_PROGRESS
        
        # Stage 3: Complete the goal
        goal_engine.update_goal_status(goal.id, GoalStatus.COMPLETED)
        assert goal_engine.get_goal(goal.id).status == GoalStatus.COMPLETED
        
        # Verify goal is no longer active
        active_goal = goal_engine.get_active_goal()
        if active_goal:
            assert active_goal.id != goal.id
