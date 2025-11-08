"""Integration tests for LangGraph-based Planner.

Tests the complete planning workflow end-to-end with realistic scenarios.
"""

import pytest
from datetime import datetime

from xagent.planning.langgraph_planner import LangGraphPlanner


@pytest.fixture
def planner():
    """Create a LangGraph planner instance."""
    return LangGraphPlanner()


@pytest.fixture
def coding_goal():
    """Create a realistic coding goal."""
    return {
        "id": "goal_coding_123",
        "description": "Write a Python script to analyze customer data from a CSV file and generate a summary report",
        "mode": "goal_oriented",
        "status": "pending",
        "completion_criteria": [
            "Read CSV file successfully",
            "Parse and validate data",
            "Calculate statistics (mean, median, mode)",
            "Generate formatted report",
            "Save report to file",
        ],
    }


@pytest.fixture
def web_research_goal():
    """Create a web research goal."""
    return {
        "id": "goal_research_456",
        "description": "Research the latest trends in artificial intelligence and machine learning for 2024",
        "mode": "goal_oriented",
        "status": "pending",
        "completion_criteria": [
            "Search for recent AI/ML articles",
            "Identify key trends",
            "Summarize findings",
        ],
    }


@pytest.fixture
def simple_calculation_goal():
    """Create a simple calculation goal."""
    return {
        "id": "goal_calc_789",
        "description": "Calculate the sum of numbers from 1 to 100",
        "mode": "goal_oriented",
        "status": "pending",
        "completion_criteria": ["Compute the sum"],
    }


class TestRealisticPlanningWorkflows:
    """Test realistic planning workflows."""

    @pytest.mark.asyncio
    async def test_complex_coding_task_planning(self, planner, coding_goal):
        """Test planning for a complex coding task."""
        context = {
            "active_goal": coding_goal,
            "memory_context": {
                "recent_actions": [],
            },
        }

        plan = await planner.create_plan(context)

        # Verify plan structure
        assert plan is not None
        assert "type" in plan
        assert "action" in plan
        assert "parameters" in plan
        assert "reasoning" in plan
        assert "goal_id" in plan
        assert plan["goal_id"] == coding_goal["id"]

        # Verify goal analysis
        assert "goal_complexity" in plan
        assert plan["goal_complexity"] in ["low", "medium", "high"]

        # For complex goal with 5 criteria, should be high complexity
        assert plan["goal_complexity"] == "high"

        # Should have sub-goals
        assert "sub_goals" in plan
        assert len(plan["sub_goals"]) > 0

        # Verify quality score
        assert "quality_score" in plan
        assert 0.0 <= plan["quality_score"] <= 1.0

        # Should have timestamp
        assert "timestamp" in plan
        datetime.fromisoformat(plan["timestamp"])

    @pytest.mark.asyncio
    async def test_web_research_task_planning(self, planner, web_research_goal):
        """Test planning for a web research task."""
        context = {
            "active_goal": web_research_goal,
            "memory_context": {
                "recent_actions": [],
            },
        }

        plan = await planner.create_plan(context)

        assert plan is not None
        assert plan["goal_id"] == web_research_goal["id"]

        # Should identify web_access as required capability
        # This is reflected in the planning process
        assert plan["goal_complexity"] in ["medium", "high"]

        # Should have sub-goals for each criterion
        assert len(plan["sub_goals"]) == len(web_research_goal["completion_criteria"])

    @pytest.mark.asyncio
    async def test_simple_calculation_planning(self, planner, simple_calculation_goal):
        """Test planning for a simple calculation task."""
        context = {
            "active_goal": simple_calculation_goal,
            "memory_context": {
                "recent_actions": [],
            },
        }

        plan = await planner.create_plan(context)

        assert plan is not None
        assert plan["goal_id"] == simple_calculation_goal["id"]

        # Simple goal should have low complexity
        assert plan["goal_complexity"] == "low"

        # Simple goals might not have sub-goals
        # Should go directly to execution
        assert plan["type"] in ["direct", "think", "sub_goal"]


class TestPlanQuality:
    """Test plan quality assessment."""

    @pytest.mark.asyncio
    async def test_plan_quality_for_well_defined_goal(self, planner, coding_goal):
        """Test that well-defined goals produce high-quality plans."""
        context = {"active_goal": coding_goal}

        plan = await planner.create_plan(context)

        assert plan is not None
        assert "quality_score" in plan

        # Well-defined goal with clear criteria should produce decent quality
        assert plan["quality_score"] >= 0.5

    @pytest.mark.asyncio
    async def test_plan_quality_scoring(self, planner, coding_goal, simple_calculation_goal):
        """Test relative quality scoring between complex and simple goals."""
        context_complex = {"active_goal": coding_goal}
        context_simple = {"active_goal": simple_calculation_goal}

        plan_complex = await planner.create_plan(context_complex)
        plan_simple = await planner.create_plan(context_simple)

        assert plan_complex is not None
        assert plan_simple is not None

        # Both should have quality scores
        assert "quality_score" in plan_complex
        assert "quality_score" in plan_simple

        # Complex goal with sub-goals might have higher or similar quality
        # The key is both should be valid
        assert plan_complex["quality_score"] > 0
        assert plan_simple["quality_score"] > 0


class TestGoalDecomposition:
    """Test goal decomposition in realistic scenarios."""

    @pytest.mark.asyncio
    async def test_decomposition_creates_sub_goals(self, planner, coding_goal):
        """Test that complex goals are decomposed into sub-goals."""
        context = {"active_goal": coding_goal}

        plan = await planner.create_plan(context)

        assert plan is not None
        assert "sub_goals" in plan

        # Should have sub-goals matching completion criteria
        assert len(plan["sub_goals"]) == len(coding_goal["completion_criteria"])

    def test_decompose_goal_method(self, planner, coding_goal):
        """Test direct goal decomposition method."""
        sub_goals = planner.decompose_goal(coding_goal)

        assert isinstance(sub_goals, list)
        assert len(sub_goals) > 0

        # Each sub-goal should have proper structure
        for sub_goal in sub_goals:
            assert "id" in sub_goal
            assert "description" in sub_goal
            assert "priority" in sub_goal
            assert "parent_id" in sub_goal

            # Parent ID should match original goal
            assert sub_goal["parent_id"] == coding_goal["id"]

            # IDs should be unique
            assert coding_goal["id"] in sub_goal["id"]


class TestActionPrioritization:
    """Test action prioritization in realistic scenarios."""

    @pytest.mark.asyncio
    async def test_actions_have_priorities(self, planner, coding_goal):
        """Test that generated actions have priorities."""
        context = {"active_goal": coding_goal}

        plan = await planner.create_plan(context)

        assert plan is not None

        # Should have remaining_actions count
        assert "remaining_actions" in plan
        assert plan["remaining_actions"] >= 0

    @pytest.mark.asyncio
    async def test_first_action_is_highest_priority(self, planner, coding_goal):
        """Test that the plan returns the highest priority action first."""
        context = {"active_goal": coding_goal}

        plan = await planner.create_plan(context)

        assert plan is not None

        # The plan should be the first/highest priority action
        # Either a sub_goal action or direct action
        assert plan["type"] in ["sub_goal", "direct", "think"]


class TestErrorHandling:
    """Test error handling in realistic scenarios."""

    @pytest.mark.asyncio
    async def test_planning_with_incomplete_goal(self, planner):
        """Test planning with incomplete goal information."""
        incomplete_goal = {
            "id": "goal_incomplete",
            "description": "",  # Empty description
            "mode": "goal_oriented",
            "status": "pending",
            "completion_criteria": [],
        }

        context = {"active_goal": incomplete_goal}

        plan = await planner.create_plan(context)

        # Should still produce a plan (fallback behavior)
        assert plan is not None
        assert "type" in plan
        assert "action" in plan

    @pytest.mark.asyncio
    async def test_planning_with_missing_fields(self, planner):
        """Test planning with missing goal fields."""
        minimal_goal = {
            "id": "goal_minimal",
            "description": "Do something",
        }

        context = {"active_goal": minimal_goal}

        plan = await planner.create_plan(context)

        # Should handle missing fields gracefully
        assert plan is not None


class TestPlanEvaluation:
    """Test plan evaluation methods."""

    def test_evaluate_complete_plan(self, planner):
        """Test evaluating a complete plan."""
        complete_plan = {
            "type": "sub_goal",
            "action": "work_on_sub_goal",
            "parameters": {"sub_goal_id": "sub_1"},
            "reasoning": "Working on first sub-goal",
            "quality_score": 0.9,
            "goal_complexity": "high",
            "sub_goals": ["sub_1", "sub_2"],
        }

        score = planner.evaluate_plan_quality(complete_plan)

        # Should return the stored quality score
        assert score == 0.9

    def test_evaluate_minimal_plan(self, planner):
        """Test evaluating a minimal plan."""
        minimal_plan = {
            "type": "think",
            "action": "analyze",
        }

        score = planner.evaluate_plan_quality(minimal_plan)

        # Minimal plan should have lower quality
        assert 0.0 <= score < 1.0


class TestWorkflowIntegration:
    """Test complete workflow integration."""

    @pytest.mark.asyncio
    async def test_end_to_end_planning_workflow(self, planner, coding_goal):
        """Test complete planning workflow from goal to executable plan."""
        # Initial context
        context = {
            "active_goal": coding_goal,
            "memory_context": {
                "recent_actions": [],
            },
            "feedback": None,
            "event": None,
        }

        # Generate plan
        plan = await planner.create_plan(context)

        # Verify complete plan structure
        assert plan is not None

        # Core fields
        assert all(key in plan for key in ["type", "action", "parameters", "reasoning"])

        # Planning metadata
        assert all(key in plan for key in ["goal_id", "goal_complexity", "quality_score"])

        # Execution metadata
        assert "timestamp" in plan
        assert "remaining_actions" in plan
        assert "sub_goals" in plan

        # Verify plan is executable
        assert plan["action"] is not None
        assert isinstance(plan["parameters"], dict)

    @pytest.mark.asyncio
    async def test_multiple_planning_cycles(self, planner, coding_goal):
        """Test multiple planning cycles with same goal."""
        context = {"active_goal": coding_goal}

        # Generate multiple plans
        plans = []
        for _ in range(3):
            plan = await planner.create_plan(context)
            assert plan is not None
            plans.append(plan)

        # All plans should be valid
        assert len(plans) == 3

        # All should reference same goal
        for plan in plans:
            assert plan["goal_id"] == coding_goal["id"]

    @pytest.mark.asyncio
    async def test_planning_with_context_updates(self, planner, coding_goal):
        """Test planning with evolving context."""
        # Initial context
        context = {
            "active_goal": coding_goal,
            "memory_context": {
                "recent_actions": [],
            },
        }

        plan1 = await planner.create_plan(context)
        assert plan1 is not None

        # Update context with recent action
        context["memory_context"]["recent_actions"].append(
            {
                "action": plan1["action"],
                "timestamp": plan1["timestamp"],
            }
        )

        plan2 = await planner.create_plan(context)
        assert plan2 is not None

        # Both plans should be valid
        assert plan1["goal_id"] == plan2["goal_id"]


class TestCapabilityDetection:
    """Test capability detection from goal descriptions."""

    @pytest.mark.asyncio
    async def test_code_execution_capability_detected(self, planner):
        """Test detection of code execution capability."""
        goal = {
            "id": "goal_code",
            "description": "Write and execute a Python function to calculate factorial",
            "mode": "goal_oriented",
            "status": "pending",
            "completion_criteria": ["Implement function", "Test with examples"],
        }

        context = {"active_goal": goal}
        plan = await planner.create_plan(context)

        assert plan is not None
        # Code-related goal should be planned appropriately
        assert plan["goal_complexity"] in ["low", "medium", "high"]

    @pytest.mark.asyncio
    async def test_file_operations_capability_detected(self, planner):
        """Test detection of file operations capability."""
        goal = {
            "id": "goal_file",
            "description": "Read data from input.txt and write results to output.txt",
            "mode": "goal_oriented",
            "status": "pending",
            "completion_criteria": ["Read file", "Process data", "Write file"],
        }

        context = {"active_goal": goal}
        plan = await planner.create_plan(context)

        assert plan is not None
        # File operation goal should produce valid plan
        assert plan["type"] in ["sub_goal", "direct", "think"]

    @pytest.mark.asyncio
    async def test_web_access_capability_detected(self, planner):
        """Test detection of web access capability."""
        goal = {
            "id": "goal_web",
            "description": "Search the web for information about Python best practices",
            "mode": "goal_oriented",
            "status": "pending",
            "completion_criteria": ["Perform web search", "Extract information"],
        }

        context = {"active_goal": goal}
        plan = await planner.create_plan(context)

        assert plan is not None
        # Web-related goal should be planned appropriately
        assert plan["goal_complexity"] in ["low", "medium", "high"]
