"""Tests for planner."""

import pytest
from xagent.core.planner import Planner


def test_planner_initialization():
    """Test planner initialization."""
    planner = Planner()
    assert planner.llm_client is None


def test_planner_initialization_with_client():
    """Test planner initialization with LLM client."""
    mock_client = object()
    planner = Planner(llm_client=mock_client)
    assert planner.llm_client is mock_client


@pytest.mark.asyncio
async def test_create_plan_without_active_goal():
    """Test plan creation without active goal."""
    planner = Planner()

    context = {
        "active_goal": None,
        "memory_context": {},
    }

    result = await planner.create_plan(context)
    assert result is None


@pytest.mark.asyncio
async def test_create_plan_with_active_goal():
    """Test plan creation with active goal."""
    planner = Planner()

    context = {
        "active_goal": {
            "id": "goal_1",
            "description": "Test goal",
            "mode": "goal_oriented",
            "status": "in_progress",
            "completion_criteria": ["Criteria 1"],
        },
        "memory_context": {"recent_actions": []},
        "feedback": "None",
        "event": "None",
    }

    plan = await planner.create_plan(context)

    assert plan is not None
    assert "type" in plan
    assert "action" in plan
    assert "parameters" in plan
    assert "reasoning" in plan
    assert "timestamp" in plan


@pytest.mark.asyncio
async def test_rule_based_planning():
    """Test rule-based planning fallback."""
    planner = Planner()

    context = {
        "active_goal": {
            "id": "goal_123",
            "description": "Analyze system",
        }
    }

    plan = planner._rule_based_planning(context)

    assert plan["type"] == "think"
    assert plan["action"] == "analyze_goal"
    assert plan["parameters"]["goal_id"] == "goal_123"
    assert "timestamp" in plan


def test_build_planning_prompt():
    """Test planning prompt generation."""
    planner = Planner()

    context = {
        "active_goal": {
            "description": "Test goal",
            "mode": "goal_oriented",
            "status": "pending",
            "completion_criteria": ["criterion1", "criterion2"],
        },
        "memory_context": {"recent_actions": ["action1"]},
        "feedback": "Good progress",
        "event": "user_input",
    }

    prompt = planner._build_planning_prompt(context)

    assert "Test goal" in prompt
    assert "goal_oriented" in prompt
    assert "criterion1" in prompt
    assert "action1" in prompt
    assert "Good progress" in prompt


def test_decompose_goal():
    """Test goal decomposition."""
    planner = Planner()

    goal = {"id": "goal_1", "description": "Complex goal"}

    sub_goals = planner.decompose_goal(goal)

    # Currently returns empty list (placeholder implementation)
    assert isinstance(sub_goals, list)
    assert len(sub_goals) == 0


def test_evaluate_plan_quality_full():
    """Test plan quality evaluation with all fields."""
    planner = Planner()

    plan = {
        "type": "think",
        "action": "analyze",
        "parameters": {"key": "value"},
        "reasoning": "test",
    }

    score = planner.evaluate_plan_quality(plan)
    assert score == 1.0


def test_evaluate_plan_quality_partial():
    """Test plan quality evaluation with partial fields."""
    planner = Planner()

    plan = {"type": "think", "action": "analyze"}

    score = planner.evaluate_plan_quality(plan)
    assert 0 < score < 1.0
    assert score == 2 / 3  # 2 out of 3 required fields


def test_evaluate_plan_quality_empty():
    """Test plan quality evaluation with no fields."""
    planner = Planner()

    plan = {}

    score = planner.evaluate_plan_quality(plan)
    assert score == 0.0


@pytest.mark.asyncio
async def test_llm_based_planning_fallback():
    """Test that LLM-based planning falls back to rule-based."""
    planner = Planner()

    context = {"active_goal": {"id": "goal_1", "description": "Test"}}

    prompt = "Test prompt"
    result = await planner._llm_based_planning(prompt, context)

    # Should fallback to rule-based
    assert result is not None
    assert result["type"] == "think"
