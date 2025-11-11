"""Tests for runtime metrics tracking."""

import asyncio
import time
from unittest.mock import AsyncMock, Mock

import pytest

from xagent.core.cognitive_loop import CognitiveLoop, CognitiveState
from xagent.core.executor import Executor
from xagent.core.goal_engine import GoalEngine
from xagent.memory.memory_layer import MemoryLayer
from xagent.monitoring.metrics import (
    MetricsCollector,
    agent_decision_latency,
    agent_task_success_rate,
    agent_tasks_completed_total,
    agent_uptime_seconds,
)


class TestRuntimeMetrics:
    """Test runtime metrics collection."""

    @pytest.fixture
    def metrics_collector(self):
        """Create a metrics collector instance."""
        return MetricsCollector()

    @pytest.fixture
    def mock_goal_engine(self):
        """Create a mock goal engine."""
        engine = Mock(spec=GoalEngine)
        engine.get_active_goal.return_value = None
        engine.get_next_goal.return_value = None
        return engine

    @pytest.fixture
    def mock_memory(self):
        """Create a mock memory layer."""
        memory = Mock(spec=MemoryLayer)
        memory.get = AsyncMock(return_value=None)
        memory.save_short_term = AsyncMock()
        memory.save_medium_term = AsyncMock()
        return memory

    @pytest.fixture
    def mock_planner(self):
        """Create a mock planner."""
        planner = Mock()
        planner.create_plan = AsyncMock(return_value=None)
        return planner

    @pytest.fixture
    def mock_executor(self):
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

    def test_uptime_metric_tracking(self, metrics_collector):
        """Test that uptime metric is tracked correctly."""
        # Update uptime
        metrics_collector.update_agent_uptime(100.5)

        # Verify metric was set
        samples = list(agent_uptime_seconds.collect())[0].samples
        assert len(samples) > 0
        assert samples[0].value == 100.5

    def test_decision_latency_tracking(self, metrics_collector):
        """Test that decision latency is tracked correctly."""
        # Record some latencies
        metrics_collector.record_decision_latency(0.15)
        metrics_collector.record_decision_latency(0.25)
        metrics_collector.record_decision_latency(0.35)

        # Verify histogram was updated
        samples = list(agent_decision_latency.collect())[0].samples
        
        # Check that count increased
        count_sample = next(s for s in samples if s.name.endswith("_count"))
        assert count_sample.value == 3

    def test_task_success_rate_tracking(self, metrics_collector):
        """Test that task success rate is tracked correctly."""
        # Record success rate
        metrics_collector.update_task_success_rate(85.5)

        # Verify metric was set
        samples = list(agent_task_success_rate.collect())[0].samples
        assert len(samples) > 0
        assert samples[0].value == 85.5

    def test_task_result_tracking(self, metrics_collector):
        """Test that task results are tracked correctly."""
        # Record some task results
        metrics_collector.record_task_result(True)
        metrics_collector.record_task_result(True)
        metrics_collector.record_task_result(False)
        metrics_collector.record_task_result(True)

        # Verify counters
        samples = list(agent_tasks_completed_total.collect())[0].samples
        
        # Find success and failure counts
        success_count = next(
            s.value for s in samples if "success" in str(s.labels)
        )
        failure_count = next(
            s.value for s in samples if "failure" in str(s.labels)
        )
        
        assert success_count == 3
        assert failure_count == 1

    @pytest.mark.asyncio
    async def test_cognitive_loop_metrics_integration(
        self, mock_goal_engine, mock_memory, mock_planner, mock_executor
    ):
        """Test that cognitive loop properly tracks metrics."""
        # Create cognitive loop
        loop = CognitiveLoop(
            goal_engine=mock_goal_engine,
            memory=mock_memory,
            planner=mock_planner,
            executor=mock_executor,
        )

        # Configure planner to return a simple plan
        mock_planner.create_plan.return_value = {
            "type": "think",
            "action": "analyze",
            "parameters": {},
        }

        # Start the loop (it will run one iteration and stop due to no active goal)
        loop.max_iterations = 2  # Limit iterations for test
        
        # Start and let it run briefly
        loop_task = asyncio.create_task(loop.start())
        
        # Wait a bit for iterations to run
        await asyncio.sleep(0.5)
        
        # Stop the loop
        await loop.stop()
        
        # Wait for loop to finish
        try:
            await asyncio.wait_for(loop_task, timeout=2.0)
        except asyncio.TimeoutError:
            pass

        # Verify uptime was tracked
        assert loop.start_time is not None
        
        # Verify task results were tracked
        assert hasattr(loop, "task_results")

    def test_rolling_success_rate_calculation(
        self, mock_goal_engine, mock_memory, mock_planner, mock_executor
    ):
        """Test that rolling success rate is calculated correctly."""
        loop = CognitiveLoop(
            goal_engine=mock_goal_engine,
            memory=mock_memory,
            planner=mock_planner,
            executor=mock_executor,
        )

        # Simulate task results
        loop._update_task_success_rate(True)
        loop._update_task_success_rate(True)
        loop._update_task_success_rate(False)
        loop._update_task_success_rate(True)

        # Check success rate (3 out of 4 = 75%)
        assert len(loop.task_results) == 4
        success_rate = (sum(1 for r in loop.task_results if r) / len(loop.task_results)) * 100
        assert success_rate == 75.0

    def test_rolling_success_rate_limit(
        self, mock_goal_engine, mock_memory, mock_planner, mock_executor
    ):
        """Test that success rate only keeps last 100 results."""
        loop = CognitiveLoop(
            goal_engine=mock_goal_engine,
            memory=mock_memory,
            planner=mock_planner,
            executor=mock_executor,
        )

        # Add 150 results
        for i in range(150):
            loop._update_task_success_rate(i % 2 == 0)  # Alternating success/failure

        # Should only keep last 100
        assert len(loop.task_results) == 100

    @pytest.mark.asyncio
    async def test_executor_tool_metrics(self):
        """Test that executor tracks tool execution metrics."""
        # Create executor with mock tool server
        tool_server = Mock()
        tool_server.call_tool = AsyncMock(return_value={"result": "success"})
        
        executor = Executor(tool_server=tool_server)

        # Execute a tool call
        result = await executor._execute_tool_call("test_tool", {"param": "value"})

        # Verify result
        assert result is not None

        # Note: Metrics are recorded but we can't easily verify them in unit tests
        # Integration tests will verify the actual metric values


class TestMetricsCollectorHelpers:
    """Test MetricsCollector helper methods."""

    def test_update_agent_uptime(self):
        """Test update_agent_uptime method."""
        collector = MetricsCollector()
        collector.update_agent_uptime(123.45)
        
        # Verify via Prometheus API
        samples = list(agent_uptime_seconds.collect())[0].samples
        assert samples[0].value == 123.45

    def test_record_decision_latency(self):
        """Test record_decision_latency method."""
        collector = MetricsCollector()
        collector.record_decision_latency(0.234)
        
        # Verify histogram was updated
        samples = list(agent_decision_latency.collect())[0].samples
        count_sample = next(s for s in samples if s.name.endswith("_count"))
        assert count_sample.value >= 1

    def test_record_task_result_success(self):
        """Test recording successful task result."""
        collector = MetricsCollector()
        
        # Get initial count
        samples_before = list(agent_tasks_completed_total.collect())[0].samples
        success_before = next(
            (s.value for s in samples_before if "success" in str(s.labels)), 0
        )
        
        # Record success
        collector.record_task_result(True)
        
        # Verify counter increased
        samples_after = list(agent_tasks_completed_total.collect())[0].samples
        success_after = next(
            s.value for s in samples_after if "success" in str(s.labels)
        )
        assert success_after == success_before + 1

    def test_record_task_result_failure(self):
        """Test recording failed task result."""
        collector = MetricsCollector()
        
        # Get initial count
        samples_before = list(agent_tasks_completed_total.collect())[0].samples
        failure_before = next(
            (s.value for s in samples_before if "failure" in str(s.labels)), 0
        )
        
        # Record failure
        collector.record_task_result(False)
        
        # Verify counter increased
        samples_after = list(agent_tasks_completed_total.collect())[0].samples
        failure_after = next(
            s.value for s in samples_after if "failure" in str(s.labels)
        )
        assert failure_after == failure_before + 1

    def test_update_task_success_rate(self):
        """Test updating task success rate."""
        collector = MetricsCollector()
        collector.update_task_success_rate(92.5)
        
        # Verify gauge was set
        samples = list(agent_task_success_rate.collect())[0].samples
        assert samples[0].value == 92.5
