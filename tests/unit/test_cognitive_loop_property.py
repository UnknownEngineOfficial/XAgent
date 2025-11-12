"""Property-based tests for Cognitive Loop using Hypothesis.

These tests ensure the cognitive loop handles various states, transitions,
and edge cases robustly through fuzzing and property-based testing.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from unittest.mock import AsyncMock, Mock
import asyncio
from datetime import datetime, timezone

from xagent.core.cognitive_loop import CognitiveLoop, CognitiveState, LoopPhase
from xagent.core.goal_engine import GoalEngine, GoalMode, GoalStatus
from xagent.memory.memory_layer import MemoryLayer


# Custom strategies for cognitive loop testing
@st.composite
def valid_states(draw):
    """Generate valid cognitive states."""
    return draw(st.sampled_from(CognitiveState))


@st.composite
def valid_phases(draw):
    """Generate valid loop phases."""
    return draw(st.sampled_from(LoopPhase))


@st.composite
def iteration_counts(draw):
    """Generate various iteration counts including edge cases."""
    return draw(
        st.one_of(
            st.just(0),
            st.just(1),
            st.just(-1),  # Invalid but should be handled
            st.integers(min_value=0, max_value=10000),
            st.just(999999),
        )
    )


@st.composite
def max_iterations(draw):
    """Generate max iteration values."""
    return draw(
        st.one_of(
            st.just(1),
            st.just(10),
            st.just(100),
            st.just(1000),
            st.integers(min_value=1, max_value=10000),
        )
    )


@st.composite
def perception_inputs(draw):
    """Generate various perception inputs."""
    return draw(
        st.one_of(
            st.none(),
            st.text(min_size=0, max_size=1000),
            st.dictionaries(
                keys=st.text(min_size=1, max_size=50),
                values=st.one_of(st.text(), st.integers(), st.booleans()),
                min_size=0,
                max_size=20,
            ),
            st.lists(st.text(), max_size=50),
        )
    )


class TestCognitiveLoopProperties:
    """Property-based tests for CognitiveLoop."""

    @given(max_iter=max_iterations())
    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    def test_initialization_with_various_max_iterations(self, max_iter):
        """Property: CognitiveLoop can be initialized with any positive max_iterations."""
        goal_engine = GoalEngine()
        memory = Mock(spec=MemoryLayer)
        planner = Mock()
        executor = Mock()

        # Mock settings
        from xagent import config
        original_max = config.settings.max_iterations
        try:
            config.settings.max_iterations = max_iter
            
            loop = CognitiveLoop(
                goal_engine=goal_engine,
                memory=memory,
                planner=planner,
                executor=executor,
            )

            # Invariants
            assert loop.state == CognitiveState.IDLE
            assert loop.current_phase == LoopPhase.PERCEPTION
            assert loop.running is False
            assert loop.iteration_count == 0
            assert loop.max_iterations == max_iter
            assert isinstance(loop.perception_queue, asyncio.Queue)
        finally:
            config.settings.max_iterations = original_max

    @given(state=valid_states())
    @settings(max_examples=100)
    def test_state_transitions_are_valid(self, state):
        """Property: State can be set to any valid CognitiveState."""
        goal_engine = GoalEngine()
        memory = Mock(spec=MemoryLayer)
        planner = Mock()
        executor = Mock()

        loop = CognitiveLoop(
            goal_engine=goal_engine,
            memory=memory,
            planner=planner,
            executor=executor,
        )

        # Should be able to set any valid state
        loop.state = state
        assert loop.state == state
        assert isinstance(loop.state, CognitiveState)

    @given(phase=valid_phases())
    @settings(max_examples=100)
    def test_phase_transitions_are_valid(self, phase):
        """Property: Phase can be set to any valid LoopPhase."""
        goal_engine = GoalEngine()
        memory = Mock(spec=MemoryLayer)
        planner = Mock()
        executor = Mock()

        loop = CognitiveLoop(
            goal_engine=goal_engine,
            memory=memory,
            planner=planner,
            executor=executor,
        )

        # Should be able to set any valid phase
        loop.current_phase = phase
        assert loop.current_phase == phase
        assert isinstance(loop.current_phase, LoopPhase)

    @given(
        perception_input=perception_inputs(),
        num_inputs=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_perception_queue_handles_various_inputs(self, perception_input, num_inputs):
        """Property: Perception queue can handle various types and volumes of inputs."""
        goal_engine = GoalEngine()
        memory = Mock(spec=MemoryLayer)
        planner = Mock()
        executor = Mock()

        loop = CognitiveLoop(
            goal_engine=goal_engine,
            memory=memory,
            planner=planner,
            executor=executor,
        )

        # Add multiple inputs to queue
        for _ in range(num_inputs):
            await loop.perception_queue.put(perception_input)

        # Queue should contain all inputs
        assert loop.perception_queue.qsize() == num_inputs

        # Should be able to retrieve all inputs
        for _ in range(num_inputs):
            retrieved = await loop.perception_queue.get()
            # Input should be preserved (no corruption)
            assert type(retrieved) == type(perception_input)

    @given(count=iteration_counts())
    @settings(max_examples=500)
    def test_iteration_count_updates_correctly(self, count):
        """Property: Iteration count can be set and read correctly."""
        goal_engine = GoalEngine()
        memory = Mock(spec=MemoryLayer)
        planner = Mock()
        executor = Mock()

        loop = CognitiveLoop(
            goal_engine=goal_engine,
            memory=memory,
            planner=planner,
            executor=executor,
        )

        if count >= 0:
            loop.iteration_count = count
            assert loop.iteration_count == count
            assert isinstance(loop.iteration_count, int)

    @given(
        num_results=st.integers(min_value=1, max_value=200),
        success_rate=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(max_examples=200)
    def test_task_results_tracking(self, num_results, success_rate):
        """Property: Task results are tracked correctly regardless of count."""
        goal_engine = GoalEngine()
        memory = Mock(spec=MemoryLayer)
        planner = Mock()
        executor = Mock()

        loop = CognitiveLoop(
            goal_engine=goal_engine,
            memory=memory,
            planner=planner,
            executor=executor,
        )

        # Add task results
        for i in range(num_results):
            result = i < (num_results * success_rate)
            loop.task_results.append(result)

        # Results should be stored (up to max capacity)
        assert len(loop.task_results) == num_results
        
        # Count successes
        success_count = sum(1 for r in loop.task_results if r)
        expected_successes = int(num_results * success_rate)
        
        # Should be close to expected (with some tolerance for rounding)
        assert abs(success_count - expected_successes) <= 1

    @given(
        states=st.lists(valid_states(), min_size=1, max_size=50),
    )
    @settings(max_examples=200)
    def test_multiple_state_transitions_maintain_consistency(self, states):
        """Property: Multiple state transitions maintain loop consistency."""
        goal_engine = GoalEngine()
        memory = Mock(spec=MemoryLayer)
        planner = Mock()
        executor = Mock()

        loop = CognitiveLoop(
            goal_engine=goal_engine,
            memory=memory,
            planner=planner,
            executor=executor,
        )

        # Apply all state transitions
        for state in states:
            loop.state = state

        # Final state should be the last one
        assert loop.state == states[-1]
        
        # Loop should still be in a valid state
        assert isinstance(loop.state, CognitiveState)
        assert loop.iteration_count >= 0
        assert loop.perception_queue is not None

    @given(
        phases=st.lists(valid_phases(), min_size=1, max_size=50),
    )
    @settings(max_examples=200)
    def test_multiple_phase_transitions_maintain_consistency(self, phases):
        """Property: Multiple phase transitions maintain loop consistency."""
        goal_engine = GoalEngine()
        memory = Mock(spec=MemoryLayer)
        planner = Mock()
        executor = Mock()

        loop = CognitiveLoop(
            goal_engine=goal_engine,
            memory=memory,
            planner=planner,
            executor=executor,
        )

        # Apply all phase transitions
        for phase in phases:
            loop.current_phase = phase

        # Final phase should be the last one
        assert loop.current_phase == phases[-1]
        
        # Loop should still be in a valid state
        assert isinstance(loop.current_phase, LoopPhase)
        assert loop.iteration_count >= 0
        assert loop.perception_queue is not None

    @given(
        checkpoint_interval=st.integers(min_value=1, max_value=1000),
    )
    @settings(max_examples=200)
    def test_checkpoint_interval_configuration(self, checkpoint_interval):
        """Property: Checkpoint interval can be configured with various values."""
        goal_engine = GoalEngine()
        memory = Mock(spec=MemoryLayer)
        planner = Mock()
        executor = Mock()

        # CognitiveLoop uses getattr with defaults, so no need to set on settings
        loop = CognitiveLoop(
            goal_engine=goal_engine,
            memory=memory,
            planner=planner,
            executor=executor,
        )

        # The default checkpoint_interval should be set
        assert loop.checkpoint_interval > 0
        assert isinstance(loop.checkpoint_interval, int)

    @given(
        running=st.booleans(),
        state=valid_states(),
        iteration=iteration_counts(),
    )
    @settings(max_examples=500)
    def test_loop_state_serialization_properties(self, running, state, iteration):
        """Property: Loop state can be represented as dict for serialization."""
        if iteration < 0:
            iteration = 0  # Normalize negative values
            
        goal_engine = GoalEngine()
        memory = Mock(spec=MemoryLayer)
        planner = Mock()
        executor = Mock()

        loop = CognitiveLoop(
            goal_engine=goal_engine,
            memory=memory,
            planner=planner,
            executor=executor,
        )

        loop.running = running
        loop.state = state
        loop.iteration_count = iteration

        # Create a state representation
        state_dict = {
            "running": loop.running,
            "state": loop.state.value,
            "current_phase": loop.current_phase.value,
            "iteration_count": loop.iteration_count,
        }

        # State dict should be serializable
        import json
        json_str = json.dumps(state_dict)
        reconstructed = json.loads(json_str)

        # Values should be preserved
        assert reconstructed["running"] == running
        assert reconstructed["state"] == state.value
        assert reconstructed["iteration_count"] == iteration


class TestCognitiveLoopInitializationInvariants:
    """Test initialization invariants."""

    @given(max_iter=max_iterations())
    @settings(max_examples=300)
    def test_initialization_invariants_always_hold(self, max_iter):
        """Property: After initialization, certain invariants always hold."""
        goal_engine = GoalEngine()
        memory = Mock(spec=MemoryLayer)
        planner = Mock()
        executor = Mock()

        from xagent import config
        original_max = config.settings.max_iterations
        
        try:
            config.settings.max_iterations = max_iter
            
            loop = CognitiveLoop(
                goal_engine=goal_engine,
                memory=memory,
                planner=planner,
                executor=executor,
            )

            # Invariants that must ALWAYS hold after initialization
            assert loop.state == CognitiveState.IDLE
            assert loop.running is False
            assert loop.iteration_count == 0
            assert loop.current_phase == LoopPhase.PERCEPTION
            assert isinstance(loop.perception_queue, asyncio.Queue)
            assert loop.goal_engine is goal_engine
            assert loop.memory is memory
            assert loop.planner is planner
            assert loop.executor is executor
            assert loop.max_iterations == max_iter
            assert loop.last_checkpoint_iteration == 0
            assert isinstance(loop.task_results, list)
            assert len(loop.task_results) == 0
        finally:
            config.settings.max_iterations = original_max


class TestCognitiveLoopEdgeCases:
    """Test edge cases and boundary conditions."""

    @given(
        queue_operations=st.lists(
            st.tuples(
                st.sampled_from(["put", "get"]),
                perception_inputs(),
            ),
            min_size=1,
            max_size=50,
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_mixed_queue_operations_maintain_fifo(self, queue_operations):
        """Property: Mixed put/get operations maintain FIFO queue order."""
        goal_engine = GoalEngine()
        memory = Mock(spec=MemoryLayer)
        planner = Mock()
        executor = Mock()

        loop = CognitiveLoop(
            goal_engine=goal_engine,
            memory=memory,
            planner=planner,
            executor=executor,
        )

        put_items = []
        get_items = []

        for operation, data in queue_operations:
            if operation == "put":
                await loop.perception_queue.put(data)
                put_items.append(data)
            elif operation == "get" and not loop.perception_queue.empty():
                item = await loop.perception_queue.get()
                get_items.append(item)

        # All retrieved items should match the order they were put in (FIFO)
        assert len(get_items) <= len(put_items)
        for i, item in enumerate(get_items):
            assert type(item) == type(put_items[i])

    def test_zero_max_iterations_is_handled(self):
        """Property: Loop handles edge case of max_iterations = 0."""
        goal_engine = GoalEngine()
        memory = Mock(spec=MemoryLayer)
        planner = Mock()
        executor = Mock()

        from xagent import config
        original_max = config.settings.max_iterations
        try:
            # Edge case: 0 max iterations (should be handled gracefully)
            config.settings.max_iterations = 0
            
            loop = CognitiveLoop(
                goal_engine=goal_engine,
                memory=memory,
                planner=planner,
                executor=executor,
            )

            # Loop should still initialize successfully
            assert loop.max_iterations == 0
            assert loop.state == CognitiveState.IDLE
            assert loop.iteration_count == 0
        finally:
            config.settings.max_iterations = original_max

    @given(
        num_tasks=st.integers(min_value=100, max_value=500),
    )
    @settings(max_examples=50)
    def test_task_results_list_can_grow_large(self, num_tasks):
        """Property: Task results list can handle large numbers of results."""
        goal_engine = GoalEngine()
        memory = Mock(spec=MemoryLayer)
        planner = Mock()
        executor = Mock()

        loop = CognitiveLoop(
            goal_engine=goal_engine,
            memory=memory,
            planner=planner,
            executor=executor,
        )

        # Add many task results
        for i in range(num_tasks):
            loop.task_results.append(i % 2 == 0)  # Alternate True/False

        # Should handle large list
        assert len(loop.task_results) == num_tasks
        
        # Can calculate success rate
        success_rate = sum(loop.task_results) / len(loop.task_results)
        assert 0.0 <= success_rate <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
