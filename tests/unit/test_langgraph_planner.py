"""Tests for LangGraph-based Planner."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from xagent.planning.langgraph_planner import (
    LangGraphPlanner,
    PlanningPhase,
    PlanningState,
)


@pytest.fixture
def planner():
    """Create a LangGraph planner instance."""
    return LangGraphPlanner()


@pytest.fixture
def sample_goal():
    """Create a sample goal."""
    return {
        "id": "goal_123",
        "description": "Write a Python script to analyze data from a CSV file",
        "mode": "goal_oriented",
        "status": "pending",
        "completion_criteria": [
            "Read CSV file successfully",
            "Parse data correctly",
            "Generate analysis report",
        ],
    }


@pytest.fixture
def simple_goal():
    """Create a simple goal."""
    return {
        "id": "goal_simple",
        "description": "Print hello world",
        "mode": "goal_oriented",
        "status": "pending",
        "completion_criteria": ["Output message"],
    }


@pytest.fixture
def context_with_goal(sample_goal):
    """Create context with active goal."""
    return {
        "active_goal": sample_goal,
        "memory_context": {
            "recent_actions": [],
        },
    }


class TestLangGraphPlannerInitialization:
    """Test planner initialization."""
    
    def test_planner_creation(self, planner):
        """Test that planner can be created."""
        assert planner is not None
        assert planner.llm is None
        assert planner.graph is not None
    
    def test_planner_with_llm(self):
        """Test planner creation with LLM."""
        mock_llm = MagicMock()
        planner = LangGraphPlanner(llm=mock_llm)
        assert planner.llm == mock_llm


class TestPlanCreation:
    """Test plan creation."""
    
    @pytest.mark.asyncio
    async def test_create_plan_with_valid_goal(self, planner, context_with_goal):
        """Test creating a plan with a valid goal."""
        plan = await planner.create_plan(context_with_goal)
        
        assert plan is not None
        assert "type" in plan
        assert "action" in plan
        assert "parameters" in plan
        assert "reasoning" in plan
        assert "goal_id" in plan
        assert plan["goal_id"] == "goal_123"
    
    @pytest.mark.asyncio
    async def test_create_plan_without_goal(self, planner):
        """Test creating a plan without an active goal."""
        context = {"active_goal": None}
        plan = await planner.create_plan(context)
        
        assert plan is None
    
    @pytest.mark.asyncio
    async def test_create_plan_with_empty_context(self, planner):
        """Test creating a plan with empty context."""
        plan = await planner.create_plan({})
        
        assert plan is None
    
    @pytest.mark.asyncio
    async def test_plan_has_timestamp(self, planner, context_with_goal):
        """Test that generated plan includes timestamp."""
        plan = await planner.create_plan(context_with_goal)
        
        assert "timestamp" in plan
        # Verify timestamp is ISO format
        datetime.fromisoformat(plan["timestamp"])


class TestGoalAnalysis:
    """Test goal analysis phase."""
    
    @pytest.mark.asyncio
    async def test_analyze_complex_goal(self, planner, sample_goal):
        """Test analyzing a complex goal."""
        state: PlanningState = {
            "goal_description": sample_goal["description"],
            "goal_id": sample_goal["id"],
            "goal_mode": sample_goal["mode"],
            "completion_criteria": sample_goal["completion_criteria"],
            "context": {},
            "current_phase": "analyze",
            "messages": [],
            "goal_complexity": None,
            "required_capabilities": [],
            "estimated_steps": None,
            "sub_goals": [],
            "dependencies": [],
            "prioritized_actions": [],
            "plan": None,
            "quality_score": None,
            "errors": [],
        }
        
        result = await planner._analyze_goal(state)
        
        assert result["goal_complexity"] in ["low", "medium", "high"]
        assert result["estimated_steps"] is not None
        assert result["estimated_steps"] > 0
        assert len(result["required_capabilities"]) > 0
        assert "code_execution" in result["required_capabilities"]
        assert "file_operations" in result["required_capabilities"]
    
    @pytest.mark.asyncio
    async def test_analyze_simple_goal(self, planner, simple_goal):
        """Test analyzing a simple goal."""
        state: PlanningState = {
            "goal_description": simple_goal["description"],
            "goal_id": simple_goal["id"],
            "goal_mode": simple_goal["mode"],
            "completion_criteria": simple_goal["completion_criteria"],
            "context": {},
            "current_phase": "analyze",
            "messages": [],
            "goal_complexity": None,
            "required_capabilities": [],
            "estimated_steps": None,
            "sub_goals": [],
            "dependencies": [],
            "prioritized_actions": [],
            "plan": None,
            "quality_score": None,
            "errors": [],
        }
        
        result = await planner._analyze_goal(state)
        
        assert result["goal_complexity"] == "low"
        assert result["estimated_steps"] <= 3


class TestGoalDecomposition:
    """Test goal decomposition phase."""
    
    @pytest.mark.asyncio
    async def test_decompose_complex_goal(self, planner, sample_goal):
        """Test decomposing a complex goal."""
        state: PlanningState = {
            "goal_description": sample_goal["description"],
            "goal_id": sample_goal["id"],
            "goal_mode": sample_goal["mode"],
            "completion_criteria": sample_goal["completion_criteria"],
            "context": {},
            "current_phase": "decompose",
            "messages": [],
            "goal_complexity": "medium",
            "required_capabilities": ["code_execution", "file_operations"],
            "estimated_steps": 4,
            "sub_goals": [],
            "dependencies": [],
            "prioritized_actions": [],
            "plan": None,
            "quality_score": None,
            "errors": [],
        }
        
        result = await planner._decompose_goal(state)
        
        assert len(result["sub_goals"]) > 0
        # Should have one sub-goal per completion criterion
        assert len(result["sub_goals"]) == len(sample_goal["completion_criteria"])
        
        # Verify sub-goals have required fields
        for sub_goal in result["sub_goals"]:
            assert "id" in sub_goal
            assert "description" in sub_goal
            assert "priority" in sub_goal
    
    @pytest.mark.asyncio
    async def test_decompose_simple_goal_skips(self, planner, simple_goal):
        """Test that simple goals skip decomposition."""
        state: PlanningState = {
            "goal_description": simple_goal["description"],
            "goal_id": simple_goal["id"],
            "goal_mode": simple_goal["mode"],
            "completion_criteria": simple_goal["completion_criteria"],
            "context": {},
            "current_phase": "decompose",
            "messages": [],
            "goal_complexity": "low",
            "required_capabilities": [],
            "estimated_steps": 2,
            "sub_goals": [],
            "dependencies": [],
            "prioritized_actions": [],
            "plan": None,
            "quality_score": None,
            "errors": [],
        }
        
        result = await planner._decompose_goal(state)
        
        # Low complexity goals should not be decomposed
        assert len(result["sub_goals"]) == 0


class TestActionPrioritization:
    """Test action prioritization phase."""
    
    @pytest.mark.asyncio
    async def test_prioritize_with_sub_goals(self, planner):
        """Test prioritizing actions with sub-goals."""
        state: PlanningState = {
            "goal_description": "Test goal",
            "goal_id": "goal_123",
            "goal_mode": "goal_oriented",
            "completion_criteria": [],
            "context": {},
            "current_phase": "prioritize",
            "messages": [],
            "goal_complexity": "medium",
            "required_capabilities": [],
            "estimated_steps": 3,
            "sub_goals": [
                {"id": "sub_1", "description": "First step", "priority": 0, "estimated_effort": 1},
                {"id": "sub_2", "description": "Second step", "priority": 1, "estimated_effort": 1},
            ],
            "dependencies": [{"from": "sub_1", "to": "sub_2", "type": "sequential"}],
            "prioritized_actions": [],
            "plan": None,
            "quality_score": None,
            "errors": [],
        }
        
        result = await planner._prioritize_actions(state)
        
        assert len(result["prioritized_actions"]) > 0
        # Should have actions for each sub-goal
        assert len(result["prioritized_actions"]) == 2
        
        # Verify actions are properly ordered
        assert result["prioritized_actions"][0]["priority"] == 0
        assert result["prioritized_actions"][1]["priority"] == 1
    
    @pytest.mark.asyncio
    async def test_prioritize_without_sub_goals(self, planner):
        """Test prioritizing actions without sub-goals."""
        state: PlanningState = {
            "goal_description": "Simple goal",
            "goal_id": "goal_simple",
            "goal_mode": "goal_oriented",
            "completion_criteria": [],
            "context": {},
            "current_phase": "prioritize",
            "messages": [],
            "goal_complexity": "low",
            "required_capabilities": [],
            "estimated_steps": 1,
            "sub_goals": [],
            "dependencies": [],
            "prioritized_actions": [],
            "plan": None,
            "quality_score": None,
            "errors": [],
        }
        
        result = await planner._prioritize_actions(state)
        
        # Should have one direct action
        assert len(result["prioritized_actions"]) == 1
        assert result["prioritized_actions"][0]["type"] == "direct"


class TestPlanValidation:
    """Test plan validation phase."""
    
    @pytest.mark.asyncio
    async def test_validate_valid_plan(self, planner):
        """Test validating a valid plan."""
        state: PlanningState = {
            "goal_description": "Test goal",
            "goal_id": "goal_123",
            "goal_mode": "goal_oriented",
            "completion_criteria": [],
            "context": {},
            "current_phase": "validate",
            "messages": [],
            "goal_complexity": "medium",
            "required_capabilities": ["code_execution"],
            "estimated_steps": 2,
            "sub_goals": [],
            "dependencies": [],
            "prioritized_actions": [
                {
                    "type": "action",
                    "action": "execute_code",
                    "parameters": {"code": "print('hello')"},
                    "reasoning": "Execute code",
                }
            ],
            "plan": None,
            "quality_score": None,
            "errors": [],
        }
        
        result = await planner._validate_plan(state)
        
        assert result["quality_score"] is not None
        assert result["quality_score"] > 0
        assert len(result["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_validate_invalid_plan(self, planner):
        """Test validating an invalid plan."""
        state: PlanningState = {
            "goal_description": "Test goal",
            "goal_id": "goal_123",
            "goal_mode": "goal_oriented",
            "completion_criteria": [],
            "context": {},
            "current_phase": "validate",
            "messages": [],
            "goal_complexity": "medium",
            "required_capabilities": [],
            "estimated_steps": 2,
            "sub_goals": [],
            "dependencies": [],
            "prioritized_actions": [],  # No actions (but will be auto-generated now)
            "plan": None,
            "quality_score": None,
            "errors": [],
        }
        
        result = await planner._validate_plan(state)
        
        # Now validation auto-generates actions for simple goals
        # So quality_score should be > 0
        assert result["quality_score"] > 0.0
        assert len(result["prioritized_actions"]) > 0


class TestPlanExecution:
    """Test plan execution phase."""
    
    @pytest.mark.asyncio
    async def test_execute_plan_generation(self, planner):
        """Test final plan generation."""
        state: PlanningState = {
            "goal_description": "Test goal",
            "goal_id": "goal_123",
            "goal_mode": "goal_oriented",
            "completion_criteria": [],
            "context": {},
            "current_phase": "execute",
            "messages": [],
            "goal_complexity": "medium",
            "required_capabilities": [],
            "estimated_steps": 2,
            "sub_goals": [{"id": "sub_1", "description": "Step"}],
            "dependencies": [],
            "prioritized_actions": [
                {
                    "type": "action",
                    "action": "work_on_goal",
                    "parameters": {"goal_id": "goal_123"},
                    "reasoning": "Start work",
                }
            ],
            "plan": None,
            "quality_score": 0.8,
            "errors": [],
        }
        
        result = await planner._execute_plan(state)
        
        assert result["plan"] is not None
        assert result["plan"]["type"] == "action"
        assert result["plan"]["action"] == "work_on_goal"
        assert "timestamp" in result["plan"]
        assert result["plan"]["goal_id"] == "goal_123"


class TestHelperMethods:
    """Test helper methods."""
    
    def test_decompose_goal_sync(self, planner, sample_goal):
        """Test synchronous goal decomposition."""
        sub_goals = planner.decompose_goal(sample_goal)
        
        assert isinstance(sub_goals, list)
        assert len(sub_goals) == len(sample_goal["completion_criteria"])
        
        for sub_goal in sub_goals:
            assert "id" in sub_goal
            assert "description" in sub_goal
            assert "priority" in sub_goal
            assert "parent_id" in sub_goal
            assert sub_goal["parent_id"] == sample_goal["id"]
    
    def test_evaluate_plan_quality_with_score(self, planner):
        """Test evaluating plan with stored quality score."""
        plan = {
            "type": "action",
            "action": "test",
            "parameters": {},
            "quality_score": 0.85,
        }
        
        score = planner.evaluate_plan_quality(plan)
        assert score == 0.85
    
    def test_evaluate_plan_quality_heuristic(self, planner):
        """Test evaluating plan using heuristic."""
        plan = {
            "type": "action",
            "action": "test",
            "parameters": {},
            "reasoning": "test reasoning",
        }
        
        score = planner.evaluate_plan_quality(plan)
        assert 0.0 <= score <= 1.0
        assert score == 1.0  # All required fields present
    
    def test_evaluate_plan_quality_with_bonuses(self, planner):
        """Test plan quality with bonus features."""
        plan = {
            "type": "action",
            "action": "test",
            "parameters": {},
            "reasoning": "test",
            "sub_goals": ["sub_1", "sub_2"],
            "goal_complexity": "high",
        }
        
        score = planner.evaluate_plan_quality(plan)
        assert score == 1.0  # Base score + bonuses (capped at 1.0)


class TestWorkflowConditionals:
    """Test workflow conditional logic."""
    
    def test_should_continue_to_prioritize_with_sub_goals(self, planner):
        """Test conditional when sub-goals exist."""
        state: PlanningState = {
            "goal_description": "",
            "goal_id": "",
            "goal_mode": "",
            "completion_criteria": [],
            "context": {},
            "current_phase": "",
            "messages": [],
            "goal_complexity": None,
            "required_capabilities": [],
            "estimated_steps": None,
            "sub_goals": [{"id": "sub_1"}],
            "dependencies": [],
            "prioritized_actions": [],
            "plan": None,
            "quality_score": None,
            "errors": [],
        }
        
        result = planner._should_continue_to_prioritize(state)
        assert result == "prioritize"
    
    def test_should_continue_without_sub_goals(self, planner):
        """Test conditional when no sub-goals."""
        state: PlanningState = {
            "goal_description": "",
            "goal_id": "",
            "goal_mode": "",
            "completion_criteria": [],
            "context": {},
            "current_phase": "",
            "messages": [],
            "goal_complexity": None,
            "required_capabilities": [],
            "estimated_steps": None,
            "sub_goals": [],
            "dependencies": [],
            "prioritized_actions": [],
            "plan": None,
            "quality_score": None,
            "errors": [],
        }
        
        result = planner._should_continue_to_prioritize(state)
        # Now skips to validate instead of execute
        assert result == "validate"
    
    def test_should_replan_with_low_quality(self, planner):
        """Test replan decision with low quality score."""
        state: PlanningState = {
            "goal_description": "",
            "goal_id": "",
            "goal_mode": "",
            "completion_criteria": [],
            "context": {},  # No replan_attempted flag
            "current_phase": "",
            "messages": [],
            "goal_complexity": None,
            "required_capabilities": [],
            "estimated_steps": None,
            "sub_goals": [],
            "dependencies": [],
            "prioritized_actions": [],
            "plan": None,
            "quality_score": 0.2,  # Low quality
            "errors": [],
        }
        
        result = planner._should_replan(state)
        assert result == "analyze"
    
    def test_should_execute_with_good_quality(self, planner):
        """Test execute decision with good quality score."""
        state: PlanningState = {
            "goal_description": "",
            "goal_id": "",
            "goal_mode": "",
            "completion_criteria": [],
            "context": {},
            "current_phase": "",
            "messages": [],
            "goal_complexity": None,
            "required_capabilities": [],
            "estimated_steps": None,
            "sub_goals": [],
            "dependencies": [],
            "prioritized_actions": [],
            "plan": None,
            "quality_score": 0.8,  # Good quality
            "errors": [],
        }
        
        result = planner._should_replan(state)
        assert result == "execute"


class TestErrorHandling:
    """Test error handling."""
    
    @pytest.mark.asyncio
    async def test_fallback_plan_on_error(self, planner, context_with_goal):
        """Test fallback plan generation on error."""
        # Mock the graph to raise an exception
        with patch.object(planner.graph, 'ainvoke', side_effect=Exception("Test error")):
            plan = await planner.create_plan(context_with_goal)
            
            # Should get fallback plan
            assert plan is not None
            assert plan["type"] == "think"
            assert plan["action"] == "analyze_goal"
            assert "reasoning" in plan
            assert "Fallback" in plan["reasoning"]
