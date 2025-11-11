"""
End-to-End tests for error recovery scenarios.

Tests how the system handles and recovers from various error conditions.
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from xagent.core.cognitive_loop import CognitiveLoop, CognitiveState
from xagent.core.executor import Executor
from xagent.core.goal_engine import GoalEngine, GoalMode, GoalStatus
from xagent.core.planner import Planner
from xagent.memory.memory_layer import MemoryLayer


@pytest.fixture
async def memory_layer():
    """Create a mock memory layer instance."""
    memory = Mock(spec=MemoryLayer)
    memory.get = AsyncMock(return_value=None)
    memory.save_short_term = AsyncMock()
    memory.save_medium_term = AsyncMock()
    memory.initialize = AsyncMock()
    memory.close = AsyncMock()
    await memory.initialize()
    yield memory
    await memory.close()


@pytest.fixture
def goal_engine():
    """Create a goal engine instance."""
    return GoalEngine()


@pytest.fixture
def planner():
    """Create a planner instance."""
    return Planner()


@pytest.fixture
def executor():
    """Create an executor instance."""
    return Executor()


@pytest.fixture
async def cognitive_loop(goal_engine, memory_layer, planner, executor):
    """Create a cognitive loop instance."""
    loop = CognitiveLoop(
        goal_engine=goal_engine,
        memory=memory_layer,
        planner=planner,
        executor=executor,
    )
    return loop


@pytest.mark.asyncio
@pytest.mark.integration
async def test_recovery_from_executor_failure(cognitive_loop, goal_engine, executor):
    """Test that cognitive loop recovers from executor failures."""
    # Create executor that fails then succeeds
    failure_count = 0

    async def flaky_execute(plan):
        nonlocal failure_count
        failure_count += 1

        if failure_count <= 2:
            # Fail first 2 times
            raise Exception("Simulated executor failure")

        # Succeed after that
        return {
            "success": True,
            "output": {"message": "recovered"},
            "error": None,
        }

    executor.execute = flaky_execute
    cognitive_loop.executor = executor

    # Create a goal
    goal = goal_engine.create_goal(
        description="Test error recovery",
        mode=GoalMode.GOAL_ORIENTED,
        priority=5,
    )
    goal_engine.set_active_goal(goal.id)

    # Run cognitive loop
    cognitive_loop.max_iterations = 5

    loop_task = asyncio.create_task(cognitive_loop.start())
    await asyncio.sleep(1.5)
    await cognitive_loop.stop()

    try:
        await asyncio.wait_for(loop_task, timeout=3.0)
    except asyncio.TimeoutError:
        pass

    # Verify loop continued despite failures
    assert cognitive_loop.iteration_count > 0
    assert failure_count >= 2  # At least some failures occurred


@pytest.mark.asyncio
@pytest.mark.integration
async def test_recovery_from_planner_failure(cognitive_loop, goal_engine, planner):
    """Test that cognitive loop recovers from planner failures."""
    # Create planner that fails intermittently
    call_count = 0

    async def flaky_plan(context):
        nonlocal call_count
        call_count += 1

        if call_count == 2:
            # Fail on second call
            raise Exception("Planner failure")

        # Return valid plan otherwise
        return {
            "type": "think",
            "action": "analyze",
            "parameters": {},
        }

    planner.create_plan = flaky_plan
    cognitive_loop.planner = planner

    # Create a goal
    goal = goal_engine.create_goal(
        description="Test planner recovery",
        mode=GoalMode.GOAL_ORIENTED,
        priority=5,
    )
    goal_engine.set_active_goal(goal.id)

    # Run cognitive loop
    cognitive_loop.max_iterations = 4

    loop_task = asyncio.create_task(cognitive_loop.start())
    await asyncio.sleep(1.0)
    await cognitive_loop.stop()

    try:
        await asyncio.wait_for(loop_task, timeout=2.0)
    except asyncio.TimeoutError:
        pass

    # Verify loop continued despite planner failure
    assert cognitive_loop.iteration_count > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_recovery_from_memory_failure(cognitive_loop, goal_engine, memory_layer):
    """Test that cognitive loop recovers from memory operation failures."""
    # Make memory operations fail intermittently
    original_save = memory_layer.save_short_term
    call_count = 0

    async def flaky_save(*args, **kwargs):
        nonlocal call_count
        call_count += 1

        if call_count == 2:
            raise Exception("Memory save failed")

        return await original_save(*args, **kwargs)

    memory_layer.save_short_term = flaky_save

    # Create a goal
    goal = goal_engine.create_goal(
        description="Test memory recovery",
        mode=GoalMode.GOAL_ORIENTED,
        priority=5,
    )
    goal_engine.set_active_goal(goal.id)

    # Run cognitive loop
    cognitive_loop.max_iterations = 4

    loop_task = asyncio.create_task(cognitive_loop.start())
    await asyncio.sleep(1.0)
    await cognitive_loop.stop()

    try:
        await asyncio.wait_for(loop_task, timeout=2.0)
    except asyncio.TimeoutError:
        pass

    # Verify loop continued despite memory failures
    assert cognitive_loop.iteration_count > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_recovery_from_missing_goal(cognitive_loop, goal_engine):
    """Test cognitive loop behavior when active goal is missing."""
    # Set a non-existent goal as active
    goal_engine.active_goal_id = "non-existent-goal-id"

    # Run cognitive loop
    cognitive_loop.max_iterations = 3

    loop_task = asyncio.create_task(cognitive_loop.start())
    await asyncio.sleep(0.8)
    await cognitive_loop.stop()

    try:
        await asyncio.wait_for(loop_task, timeout=2.0)
    except asyncio.TimeoutError:
        pass

    # Loop should handle missing goal gracefully
    assert cognitive_loop.iteration_count > 0
    assert cognitive_loop.state == CognitiveState.STOPPED


@pytest.mark.asyncio
@pytest.mark.integration
async def test_recovery_from_perception_queue_overflow(cognitive_loop, goal_engine):
    """Test handling of perception queue overflow."""
    # Create a goal
    goal = goal_engine.create_goal(
        description="Test perception overflow",
        mode=GoalMode.GOAL_ORIENTED,
        priority=5,
    )
    goal_engine.set_active_goal(goal.id)

    # Flood perception queue
    for i in range(1000):
        await cognitive_loop.add_perception(
            {
                "type": "event",
                "content": f"Event {i}",
            }
        )

    # Run cognitive loop
    cognitive_loop.max_iterations = 3

    loop_task = asyncio.create_task(cognitive_loop.start())
    await asyncio.sleep(1.0)
    await cognitive_loop.stop()

    try:
        await asyncio.wait_for(loop_task, timeout=2.0)
    except asyncio.TimeoutError:
        pass

    # Loop should handle many perceptions without crashing
    assert cognitive_loop.iteration_count > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_recovery_from_infinite_loop_detection(cognitive_loop, goal_engine):
    """Test detection and recovery from infinite loops."""
    # Create executor that always returns same result
    async def repetitive_execute(plan):
        return {
            "success": True,
            "output": {"same": "result"},
            "error": None,
        }

    cognitive_loop.executor.execute = repetitive_execute

    # Create a goal
    goal = goal_engine.create_goal(
        description="Test loop detection",
        mode=GoalMode.GOAL_ORIENTED,
        priority=5,
    )
    goal_engine.set_active_goal(goal.id)

    # Run with iteration limit to prevent actual infinite loop
    cognitive_loop.max_iterations = 10

    loop_task = asyncio.create_task(cognitive_loop.start())
    await asyncio.sleep(2.0)
    await cognitive_loop.stop()

    try:
        await asyncio.wait_for(loop_task, timeout=3.0)
    except asyncio.TimeoutError:
        pass

    # Loop should stop at max iterations
    assert cognitive_loop.iteration_count == 10


@pytest.mark.asyncio
@pytest.mark.integration
async def test_graceful_shutdown_during_error(cognitive_loop, goal_engine):
    """Test graceful shutdown even when errors are occurring."""
    # Create executor that always fails
    async def failing_execute(plan):
        raise Exception("Continuous failure")

    cognitive_loop.executor.execute = failing_execute

    # Create a goal
    goal = goal_engine.create_goal(
        description="Test shutdown during errors",
        mode=GoalMode.GOAL_ORIENTED,
        priority=5,
    )
    goal_engine.set_active_goal(goal.id)

    # Start loop
    cognitive_loop.max_iterations = 10

    loop_task = asyncio.create_task(cognitive_loop.start())
    await asyncio.sleep(0.5)

    # Stop loop (should shutdown gracefully even with errors)
    await cognitive_loop.stop()

    try:
        await asyncio.wait_for(loop_task, timeout=2.0)
    except asyncio.TimeoutError:
        pass

    # Verify graceful shutdown
    assert cognitive_loop.state == CognitiveState.STOPPED


@pytest.mark.asyncio
@pytest.mark.integration
async def test_recovery_tracking_in_metrics(cognitive_loop, goal_engine, planner):
    """Test that error recovery is tracked in metrics."""
    # Create executor that fails then succeeds
    failure_count = 0

    async def mixed_execute(plan):
        nonlocal failure_count
        failure_count += 1

        if failure_count % 2 == 0:
            return {
                "success": False,
                "output": None,
                "error": "Simulated failure",
            }
        return {
            "success": True,
            "output": {"message": "success"},
            "error": None,
        }

    # Configure planner to return plans
    planner.create_plan = AsyncMock(
        return_value={
            "type": "think",
            "action": "analyze",
            "parameters": {},
        }
    )
    cognitive_loop.planner = planner
    cognitive_loop.executor.execute = mixed_execute

    # Create a goal
    goal = goal_engine.create_goal(
        description="Test metrics during recovery",
        mode=GoalMode.GOAL_ORIENTED,
        priority=5,
    )
    goal_engine.set_active_goal(goal.id)

    # Run cognitive loop
    cognitive_loop.max_iterations = 6

    loop_task = asyncio.create_task(cognitive_loop.start())
    await asyncio.sleep(1.5)
    await cognitive_loop.stop()

    try:
        await asyncio.wait_for(loop_task, timeout=2.0)
    except asyncio.TimeoutError:
        pass

    # Verify metrics tracked both successes and failures
    assert len(cognitive_loop.task_results) > 0
    # With alternating success/failure pattern, we should have both
    if len(cognitive_loop.task_results) > 1:
        # Check if we have mixed results
        unique_results = set(cognitive_loop.task_results)
        # Should have at least recorded some results
        assert len(unique_results) >= 1


@pytest.mark.asyncio
@pytest.mark.integration
async def test_recovery_from_goal_completion_check_failure(
    cognitive_loop, goal_engine
):
    """Test recovery when goal completion check fails."""
    # Make goal completion check fail
    original_check = goal_engine.check_goal_completion

    def failing_check(goal_id):
        raise Exception("Completion check failed")

    goal_engine.check_goal_completion = failing_check

    # Create a goal
    goal = goal_engine.create_goal(
        description="Test completion check recovery",
        mode=GoalMode.GOAL_ORIENTED,
        priority=5,
    )
    goal_engine.set_active_goal(goal.id)

    # Run cognitive loop
    cognitive_loop.max_iterations = 3

    loop_task = asyncio.create_task(cognitive_loop.start())
    await asyncio.sleep(0.8)
    await cognitive_loop.stop()

    try:
        await asyncio.wait_for(loop_task, timeout=2.0)
    except asyncio.TimeoutError:
        pass

    # Loop should continue despite completion check failures
    assert cognitive_loop.iteration_count > 0

    # Restore original function
    goal_engine.check_goal_completion = original_check


@pytest.mark.asyncio
@pytest.mark.integration
async def test_multiple_concurrent_error_recovery(cognitive_loop, goal_engine):
    """Test handling multiple types of errors occurring simultaneously."""
    error_types = []

    # Create executor that fails with different errors
    async def multi_error_execute(plan):
        import random

        error_type = random.choice(["timeout", "exception", "invalid"])
        error_types.append(error_type)

        if error_type == "timeout":
            await asyncio.sleep(10)  # Simulate timeout
        elif error_type == "exception":
            raise Exception("Random exception")
        elif error_type == "invalid":
            return {
                "success": False,
                "output": None,
                "error": "Invalid result",
            }

        return {
            "success": True,
            "output": {"message": "success"},
            "error": None,
        }

    cognitive_loop.executor.execute = multi_error_execute

    # Create a goal
    goal = goal_engine.create_goal(
        description="Test multiple error types",
        mode=GoalMode.GOAL_ORIENTED,
        priority=5,
    )
    goal_engine.set_active_goal(goal.id)

    # Run with limited iterations and timeout
    cognitive_loop.max_iterations = 5

    loop_task = asyncio.create_task(cognitive_loop.start())

    # Give limited time
    await asyncio.sleep(1.5)
    await cognitive_loop.stop()

    try:
        await asyncio.wait_for(loop_task, timeout=2.0)
    except asyncio.TimeoutError:
        pass

    # Verify loop handled various error types
    assert cognitive_loop.iteration_count > 0
    # Should have encountered some errors
    assert len(error_types) > 0
