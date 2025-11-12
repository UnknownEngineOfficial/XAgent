"""Performance benchmarks for the cognitive loop."""

import asyncio
import time
from typing import Any

import pytest
import pytest_asyncio

from xagent.core.cognitive_loop import CognitiveLoop, CognitiveState
from xagent.core.goal_engine import Goal, GoalEngine
from xagent.memory.memory_layer import MemoryLayer


class MockPlanner:
    """Mock planner for benchmarking."""

    async def plan(self, goal: Goal, context: dict[str, Any]) -> dict[str, Any]:
        """Mock planning that simulates real work."""
        await asyncio.sleep(0.01)  # Simulate LLM call latency
        return {
            "actions": [
                {"type": "think", "content": "Planning step 1"},
                {"type": "think", "content": "Planning step 2"},
            ],
            "confidence": 0.9,
        }


class MockExecutor:
    """Mock executor for benchmarking."""

    async def execute(self, action: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """Mock execution that simulates real work."""
        await asyncio.sleep(0.005)  # Simulate tool execution
        return {"status": "success", "result": "Action executed"}


@pytest_asyncio.fixture
async def cognitive_loop():
    """Create a cognitive loop for benchmarking."""
    goal_engine = GoalEngine()
    memory = MemoryLayer()
    planner = MockPlanner()
    executor = MockExecutor()

    loop = CognitiveLoop(
        goal_engine=goal_engine,
        memory=memory,
        planner=planner,
        executor=executor,
        max_iterations=100,
    )

    yield loop


@pytest.mark.benchmark(group="cognitive_loop")
@pytest.mark.asyncio
async def test_single_iteration_latency(cognitive_loop, benchmark):
    """Benchmark single cognitive loop iteration latency.
    
    Target: < 50ms per iteration
    """
    
    async def run_single_iteration():
        """Run one iteration."""
        # Add a simple goal
        goal = Goal(
            goal_id="benchmark_goal",
            description="Simple benchmark goal",
            status="in_progress",
        )
        cognitive_loop.goal_engine.add_goal(goal)
        
        # Run one iteration
        cognitive_loop.state = CognitiveState.IDLE
        await cognitive_loop._perception_phase()
        await cognitive_loop._interpretation_phase()
        await cognitive_loop._planning_phase()
        await cognitive_loop._execution_phase()
        await cognitive_loop._reflection_phase()
        
        return True
    
    # Benchmark the iteration
    result = benchmark.pedantic(
        lambda: asyncio.run(run_single_iteration()),
        iterations=10,
        rounds=5,
    )
    
    assert result


@pytest.mark.benchmark(group="cognitive_loop")
@pytest.mark.asyncio
async def test_loop_throughput(cognitive_loop, benchmark):
    """Benchmark cognitive loop throughput.
    
    Target: > 10 iterations/second
    """
    
    async def run_iterations():
        """Run multiple iterations."""
        goal = Goal(
            goal_id="throughput_goal",
            description="Throughput benchmark goal",
            status="in_progress",
        )
        cognitive_loop.goal_engine.add_goal(goal)
        
        iterations = 0
        max_iterations = 50
        
        while iterations < max_iterations and cognitive_loop.state != CognitiveState.STOPPED:
            await cognitive_loop._perception_phase()
            await cognitive_loop._interpretation_phase()
            await cognitive_loop._planning_phase()
            await cognitive_loop._execution_phase()
            await cognitive_loop._reflection_phase()
            iterations += 1
        
        return iterations
    
    result = benchmark.pedantic(
        lambda: asyncio.run(run_iterations()),
        iterations=3,
        rounds=2,
    )
    
    # Should complete all iterations
    assert result == 50


@pytest.mark.benchmark(group="memory")
@pytest.mark.asyncio
async def test_memory_write_performance(benchmark):
    """Benchmark memory write operations.
    
    Target: > 100 writes/second
    """
    memory = MemoryLayer()
    
    async def write_memories():
        """Write multiple memories."""
        for i in range(100):
            await memory.add_memory(
                content=f"Memory content {i}",
                memory_type="perception",
                importance=0.5,
                metadata={"source": "benchmark"},
            )
        return 100
    
    result = benchmark.pedantic(
        lambda: asyncio.run(write_memories()),
        iterations=5,
        rounds=3,
    )
    
    assert result == 100


@pytest.mark.benchmark(group="memory")
@pytest.mark.asyncio
async def test_memory_read_performance(benchmark):
    """Benchmark memory read operations.
    
    Target: < 10ms per read
    """
    memory = MemoryLayer()
    
    # Pre-populate memory
    async def populate():
        for i in range(100):
            await memory.add_memory(
                content=f"Memory content {i}",
                memory_type="perception",
                importance=0.5,
                metadata={"source": "benchmark"},
            )
    
    asyncio.run(populate())
    
    async def read_memories():
        """Read recent memories."""
        memories = await memory.get_recent_memories(limit=10)
        return len(memories)
    
    result = benchmark.pedantic(
        lambda: asyncio.run(read_memories()),
        iterations=10,
        rounds=5,
    )
    
    assert result >= 0


@pytest.mark.benchmark(group="planning")
@pytest.mark.asyncio
async def test_planning_latency(benchmark):
    """Benchmark planning operation latency.
    
    Target: < 100ms for simple plans
    """
    planner = MockPlanner()
    goal = Goal(
        goal_id="planning_benchmark",
        description="Complex planning task with multiple subtasks",
        status="pending",
    )
    
    async def run_planning():
        """Run planning."""
        plan = await planner.plan(goal, {})
        return len(plan.get("actions", []))
    
    result = benchmark.pedantic(
        lambda: asyncio.run(run_planning()),
        iterations=10,
        rounds=5,
    )
    
    assert result > 0


@pytest.mark.benchmark(group="execution")
@pytest.mark.asyncio
async def test_action_execution_latency(benchmark):
    """Benchmark action execution latency.
    
    Target: < 20ms for simple actions
    """
    executor = MockExecutor()
    action = {"type": "think", "content": "Simple thinking action"}
    
    async def execute_action():
        """Execute a single action."""
        result = await executor.execute(action, {})
        return result["status"]
    
    result = benchmark.pedantic(
        lambda: asyncio.run(execute_action()),
        iterations=10,
        rounds=5,
    )
    
    assert result == "success"


@pytest.mark.benchmark(group="goal_engine")
def test_goal_creation_performance(benchmark):
    """Benchmark goal creation and management.
    
    Target: > 1000 goals/second
    """
    goal_engine = GoalEngine()
    
    def create_goals():
        """Create multiple goals."""
        for i in range(100):
            goal = Goal(
                goal_id=f"goal_{i}",
                description=f"Benchmark goal {i}",
                status="pending",
            )
            goal_engine.add_goal(goal)
        return 100
    
    result = benchmark.pedantic(
        create_goals,
        iterations=10,
        rounds=5,
    )
    
    assert result == 100


@pytest.mark.benchmark(group="goal_engine")
def test_goal_query_performance(benchmark):
    """Benchmark goal query performance.
    
    Target: < 1ms for queries
    """
    goal_engine = GoalEngine()
    
    # Pre-populate with goals
    for i in range(1000):
        goal = Goal(
            goal_id=f"goal_{i}",
            description=f"Benchmark goal {i}",
            status="pending" if i % 2 == 0 else "completed",
        )
        goal_engine.add_goal(goal)
    
    def query_goals():
        """Query goals by status."""
        pending_goals = goal_engine.get_goals_by_status("pending")
        return len(pending_goals)
    
    result = benchmark.pedantic(
        query_goals,
        iterations=10,
        rounds=5,
    )
    
    assert result == 500


@pytest.mark.benchmark(group="integration")
@pytest.mark.asyncio
async def test_end_to_end_workflow_performance(cognitive_loop, benchmark):
    """Benchmark complete end-to-end workflow.
    
    Target: < 5 seconds for 10 iterations
    """
    
    async def run_workflow():
        """Run a complete workflow."""
        # Create hierarchical goals
        parent_goal = Goal(
            goal_id="parent",
            description="Parent goal",
            status="in_progress",
        )
        cognitive_loop.goal_engine.add_goal(parent_goal)
        
        for i in range(3):
            child_goal = Goal(
                goal_id=f"child_{i}",
                description=f"Child goal {i}",
                status="pending",
                parent_id="parent",
            )
            cognitive_loop.goal_engine.add_goal(child_goal)
        
        # Run iterations
        iterations = 0
        max_iterations = 10
        
        while iterations < max_iterations:
            await cognitive_loop._perception_phase()
            await cognitive_loop._interpretation_phase()
            await cognitive_loop._planning_phase()
            await cognitive_loop._execution_phase()
            await cognitive_loop._reflection_phase()
            iterations += 1
        
        return iterations
    
    result = benchmark.pedantic(
        lambda: asyncio.run(run_workflow()),
        iterations=3,
        rounds=2,
    )
    
    assert result == 10


# Stress tests
@pytest.mark.benchmark(group="stress")
@pytest.mark.asyncio
async def test_high_load_concurrent_operations(benchmark):
    """Benchmark system under high concurrent load.
    
    Target: Handle 100 concurrent operations
    """
    
    async def concurrent_operations():
        """Run many concurrent operations."""
        tasks = []
        
        for i in range(100):
            # Mix of different operations
            if i % 3 == 0:
                # Memory write
                memory = MemoryLayer()
                tasks.append(
                    memory.add_memory(
                        content=f"Concurrent memory {i}",
                        memory_type="perception",
                        importance=0.5,
                    )
                )
            elif i % 3 == 1:
                # Goal creation
                goal_engine = GoalEngine()
                goal = Goal(
                    goal_id=f"concurrent_{i}",
                    description=f"Concurrent goal {i}",
                    status="pending",
                )
                goal_engine.add_goal(goal)
            else:
                # Planning simulation
                planner = MockPlanner()
                goal = Goal(goal_id=f"plan_{i}", description="Plan", status="pending")
                tasks.append(planner.plan(goal, {}))
        
        # Wait for all async tasks
        if tasks:
            await asyncio.gather(*tasks)
        
        return len(tasks)
    
    result = benchmark.pedantic(
        lambda: asyncio.run(concurrent_operations()),
        iterations=3,
        rounds=2,
    )
    
    assert result >= 0


if __name__ == "__main__":
    """Run benchmarks directly."""
    pytest.main([__file__, "--benchmark-only", "-v"])
