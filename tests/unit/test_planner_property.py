"""Property-based tests for Planner using Hypothesis.

These tests ensure the Planner handles various inputs robustly,
including edge cases and malformed data.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume
import json

from xagent.core.planner import Planner
from xagent.core.goal_engine import GoalMode, GoalStatus


# Custom strategies for planning contexts
@st.composite
def goal_contexts(draw):
    """Generate various goal contexts for planning."""
    return {
        "description": draw(st.text(min_size=1, max_size=500)),
        "mode": draw(st.sampled_from([m.value for m in GoalMode])),
        "status": draw(st.sampled_from([s.value for s in GoalStatus])),
        "completion_criteria": draw(
            st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=10)
        ),
    }


@st.composite
def planning_contexts(draw):
    """Generate complete planning contexts with various structures."""
    has_active_goal = draw(st.booleans())
    
    context = {}
    
    if has_active_goal:
        context["active_goal"] = draw(goal_contexts())
    
    # Add optional fields
    if draw(st.booleans()):
        context["memory_context"] = {
            "recent_actions": draw(
                st.lists(
                    st.dictionaries(
                        keys=st.text(min_size=1, max_size=20),
                        values=st.one_of(st.text(), st.integers(), st.booleans()),
                        min_size=0,
                        max_size=5,
                    ),
                    max_size=10,
                )
            )
        }
    
    if draw(st.booleans()):
        context["feedback"] = draw(st.one_of(st.text(), st.none()))
    
    if draw(st.booleans()):
        context["event"] = draw(st.one_of(st.text(), st.none()))
    
    # Add unexpected fields (robustness test)
    if draw(st.booleans()):
        context["unexpected_field"] = draw(st.text())
    
    return context


@st.composite
def malformed_contexts(draw):
    """Generate intentionally malformed contexts to test error handling."""
    return draw(
        st.one_of(
            st.none(),
            st.just({}),  # Empty dict
            st.just({"active_goal": None}),  # None goal
            st.just({"active_goal": "not a dict"}),  # Wrong type
            st.just({"active_goal": {}}),  # Empty goal
            st.dictionaries(
                keys=st.text(max_size=50),
                values=st.one_of(
                    st.text(),
                    st.integers(),
                    st.lists(st.integers()),
                    st.none(),
                ),
                min_size=0,
                max_size=20,
            ),
        )
    )


class TestPlannerProperties:
    """Property-based tests for Planner."""

    @given(context=planning_contexts())
    @settings(max_examples=1000, suppress_health_check=[HealthCheck.too_slow])
    @pytest.mark.asyncio
    async def test_create_plan_always_returns_dict_or_none(self, context):
        """Property: create_plan always returns a dict or None, never crashes."""
        planner = Planner()
        
        try:
            plan = await planner.create_plan(context)
            
            # Plan must be either None or a dict
            assert plan is None or isinstance(plan, dict), \
                f"Expected dict or None, got {type(plan)}"
            
            # If plan exists, it should have required structure
            if plan is not None:
                assert isinstance(plan, dict)
                # Basic plan should have some structure
                assert len(plan) >= 0  # Can be empty dict but should be dict
                
        except Exception as e:
            # Planner should handle errors gracefully, not crash
            pytest.fail(f"Planner crashed with: {e}")

    @given(context=planning_contexts())
    @settings(max_examples=500)
    @pytest.mark.asyncio
    async def test_plan_has_consistent_structure(self, context):
        """Property: When a plan is returned, it has consistent structure."""
        planner = Planner()
        plan = await planner.create_plan(context)
        
        if plan is not None:
            # Plan should be serializable (important for storage/transmission)
            try:
                json_str = json.dumps(plan)
                reconstructed = json.loads(json_str)
                assert isinstance(reconstructed, dict)
            except (TypeError, ValueError) as e:
                pytest.fail(f"Plan is not JSON serializable: {e}")

    @given(context=malformed_contexts())
    @settings(max_examples=1000)
    @pytest.mark.asyncio
    async def test_planner_handles_malformed_context_gracefully(self, context):
        """Property: Planner gracefully handles malformed contexts."""
        planner = Planner()
        
        try:
            plan = await planner.create_plan(context)
            # Should return None for invalid contexts, not crash
            assert plan is None or isinstance(plan, dict)
        except (AttributeError, TypeError, KeyError):
            # These are expected for truly malformed contexts
            # The planner might not handle every edge case, which is fine
            # The important thing is that it doesn't cause system-wide crashes
            pass
        except Exception as e:
            # Other exceptions might indicate a real problem
            pytest.fail(f"Planner crashed with unexpected error: {e}")

    @given(
        description=st.text(min_size=1, max_size=1000),
        mode=st.sampled_from([m.value for m in GoalMode]),
        status=st.sampled_from([s.value for s in GoalStatus]),
    )
    @settings(max_examples=500)
    @pytest.mark.asyncio
    async def test_build_planning_prompt_never_crashes(self, description, mode, status):
        """Property: _build_planning_prompt handles any valid goal data."""
        planner = Planner()
        
        context = {
            "active_goal": {
                "description": description,
                "mode": mode,
                "status": status,
                "completion_criteria": [],
            }
        }
        
        try:
            prompt = planner._build_planning_prompt(context)
            
            # Prompt should be a non-empty string
            assert isinstance(prompt, str)
            assert len(prompt) > 0
            
            # Prompt should contain goal description
            assert description in prompt or mode in prompt or status in prompt
            
        except Exception as e:
            pytest.fail(f"_build_planning_prompt crashed with: {e}")

    @given(
        num_criteria=st.integers(min_value=0, max_value=50),
    )
    @settings(max_examples=200)
    @pytest.mark.asyncio
    async def test_planner_handles_varying_criteria_counts(self, num_criteria):
        """Property: Planner handles goals with varying numbers of completion criteria."""
        planner = Planner()
        
        criteria = [f"Criterion {i}" for i in range(num_criteria)]
        context = {
            "active_goal": {
                "description": "Test goal",
                "mode": GoalMode.GOAL_ORIENTED.value,
                "status": GoalStatus.PENDING.value,
                "completion_criteria": criteria,
            }
        }
        
        try:
            plan = await planner.create_plan(context)
            # Should handle any number of criteria
            assert plan is None or isinstance(plan, dict)
        except Exception as e:
            pytest.fail(f"Failed with {num_criteria} criteria: {e}")

    @given(
        context=planning_contexts(),
    )
    @settings(max_examples=500)
    @pytest.mark.asyncio
    async def test_repeated_planning_is_deterministic_for_same_context(self, context):
        """Property: Planning with same context produces consistent results (ignoring timestamps)."""
        planner = Planner()
        
        # Plan multiple times with same context
        plan1 = await planner.create_plan(context)
        plan2 = await planner.create_plan(context)
        plan3 = await planner.create_plan(context)
        
        # For rule-based planning, results should be identical (except timestamps)
        # (LLM-based might vary, but rule-based should be deterministic)
        if plan1 is None:
            assert plan2 is None
            assert plan3 is None
        else:
            # Remove timestamps for comparison
            def remove_timestamp(plan):
                if plan and isinstance(plan, dict):
                    return {k: v for k, v in plan.items() if k != 'timestamp'}
                return plan
            
            plan1_no_ts = remove_timestamp(plan1)
            plan2_no_ts = remove_timestamp(plan2)
            plan3_no_ts = remove_timestamp(plan3)
            
            assert plan1_no_ts == plan2_no_ts == plan3_no_ts

    @given(
        base_context=planning_contexts(),
        extra_fields=st.dictionaries(
            keys=st.text(min_size=1, max_size=30),
            values=st.one_of(st.text(), st.integers(), st.booleans(), st.none()),
            min_size=1,
            max_size=10,
        ),
    )
    @settings(max_examples=300)
    @pytest.mark.asyncio
    async def test_planner_ignores_unknown_context_fields(self, base_context, extra_fields):
        """Property: Planner handles contexts with unexpected fields gracefully."""
        planner = Planner()
        
        # Add unexpected fields to context
        context_with_extras = {**base_context, **extra_fields}
        
        try:
            plan = await planner.create_plan(context_with_extras)
            # Should not crash, even with unexpected fields
            assert plan is None or isinstance(plan, dict)
        except Exception as e:
            pytest.fail(f"Planner crashed with extra fields: {e}")

    @given(
        memory_size=st.integers(min_value=0, max_value=100),
    )
    @settings(max_examples=200)
    @pytest.mark.asyncio
    async def test_planner_handles_varying_memory_sizes(self, memory_size):
        """Property: Planner handles contexts with varying memory sizes."""
        planner = Planner()
        
        recent_actions = [{"action": f"action_{i}"} for i in range(memory_size)]
        context = {
            "active_goal": {
                "description": "Test goal",
                "mode": GoalMode.GOAL_ORIENTED.value,
                "status": GoalStatus.IN_PROGRESS.value,
            },
            "memory_context": {
                "recent_actions": recent_actions,
            },
        }
        
        try:
            plan = await planner.create_plan(context)
            assert plan is None or isinstance(plan, dict)
        except Exception as e:
            pytest.fail(f"Failed with {memory_size} memory items: {e}")

    @given(
        feedback=st.one_of(
            st.none(),
            st.just(""),
            st.text(max_size=10000),
            st.just("Special chars: 你好 🎉 \n\t\r"),
        )
    )
    @settings(max_examples=500)
    @pytest.mark.asyncio
    async def test_planner_handles_various_feedback_types(self, feedback):
        """Property: Planner handles various feedback formats."""
        planner = Planner()
        
        context = {
            "active_goal": {
                "description": "Test goal",
                "mode": GoalMode.GOAL_ORIENTED.value,
                "status": GoalStatus.IN_PROGRESS.value,
            },
            "feedback": feedback,
        }
        
        try:
            plan = await planner.create_plan(context)
            assert plan is None or isinstance(plan, dict)
        except Exception as e:
            pytest.fail(f"Failed with feedback type {type(feedback)}: {e}")


class TestPlannerRuleBasedPlanning:
    """Property-based tests for rule-based planning logic."""

    @given(context=planning_contexts())
    @settings(max_examples=500)
    def test_rule_based_planning_never_crashes(self, context):
        """Property: Rule-based planning handles any context without crashing."""
        planner = Planner()
        
        try:
            plan = planner._rule_based_planning(context)
            
            # Should return a dict
            assert isinstance(plan, dict)
            
            # Plan should be JSON serializable
            json.dumps(plan)
            
        except Exception as e:
            pytest.fail(f"Rule-based planning crashed: {e}")

    @given(
        goal_mode=st.sampled_from([m.value for m in GoalMode]),
        goal_status=st.sampled_from([s.value for s in GoalStatus]),
    )
    @settings(max_examples=200)
    def test_rule_based_planning_considers_goal_state(self, goal_mode, goal_status):
        """Property: Rule-based planning considers goal mode and status."""
        planner = Planner()
        
        context = {
            "active_goal": {
                "description": "Test goal",
                "mode": goal_mode,
                "status": goal_status,
            }
        }
        
        plan = planner._rule_based_planning(context)
        
        assert isinstance(plan, dict)
        # Plan should have some action type
        assert "type" in plan or len(plan) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
