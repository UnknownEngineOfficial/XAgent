"""Integration tests for Agent with both planners."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from xagent.core.agent import XAgent
from xagent.config import Settings
from xagent.core.goal_engine import GoalMode


@pytest.mark.asyncio
class TestAgentPlannerIntegration:
    """Test agent works with both legacy and LangGraph planners."""
    
    async def test_agent_with_legacy_planner(self):
        """Test agent initialization with legacy planner."""
        settings = Settings(use_langgraph_planner=False)
        agent = XAgent(settings=settings)
        
        assert agent.planner is not None
        assert agent.planner.__class__.__name__ == "Planner"
        assert not agent.initialized
        
    async def test_agent_with_langgraph_planner(self):
        """Test agent initialization with LangGraph planner."""
        settings = Settings(use_langgraph_planner=True)
        agent = XAgent(settings=settings)
        
        assert agent.planner is not None
        assert agent.planner.__class__.__name__ == "LangGraphPlanner"
        assert not agent.initialized
    
    async def test_agent_status_includes_planner_type_legacy(self):
        """Test agent status includes planner type for legacy planner."""
        settings = Settings(use_langgraph_planner=False)
        agent = XAgent(settings=settings)
        
        # Mock memory to avoid actual initialization
        agent.memory.initialize = AsyncMock()
        agent.memory.close = AsyncMock()
        await agent.initialize()
        
        status = await agent.get_status()
        
        assert "planner_type" in status
        assert status["planner_type"] == "legacy"
    
    async def test_agent_status_includes_planner_type_langgraph(self):
        """Test agent status includes planner type for LangGraph planner."""
        settings = Settings(use_langgraph_planner=True)
        agent = XAgent(settings=settings)
        
        # Mock memory to avoid actual initialization
        agent.memory.initialize = AsyncMock()
        agent.memory.close = AsyncMock()
        await agent.initialize()
        
        status = await agent.get_status()
        
        assert "planner_type" in status
        assert status["planner_type"] == "langgraph"
    
    async def test_create_goal_with_legacy_planner(self):
        """Test creating goals works with legacy planner."""
        settings = Settings(use_langgraph_planner=False)
        agent = XAgent(settings=settings)
        
        # Create a goal
        goal = agent.goal_engine.create_goal(
            description="Test goal with legacy planner",
            mode=GoalMode.GOAL_ORIENTED,
            priority=5
        )
        
        assert goal is not None
        assert goal.description == "Test goal with legacy planner"
        assert goal.mode == GoalMode.GOAL_ORIENTED
    
    async def test_create_goal_with_langgraph_planner(self):
        """Test creating goals works with LangGraph planner."""
        settings = Settings(use_langgraph_planner=True)
        agent = XAgent(settings=settings)
        
        # Create a goal
        goal = agent.goal_engine.create_goal(
            description="Test goal with LangGraph planner",
            mode=GoalMode.GOAL_ORIENTED,
            priority=5
        )
        
        assert goal is not None
        assert goal.description == "Test goal with LangGraph planner"
        assert goal.mode == GoalMode.GOAL_ORIENTED
    
    async def test_planner_create_plan_interface_legacy(self):
        """Test legacy planner has correct interface."""
        settings = Settings(use_langgraph_planner=False)
        agent = XAgent(settings=settings)
        
        # Test planner has create_plan method
        assert hasattr(agent.planner, "create_plan")
        assert callable(agent.planner.create_plan)
    
    async def test_planner_create_plan_interface_langgraph(self):
        """Test LangGraph planner has correct interface."""
        settings = Settings(use_langgraph_planner=True)
        agent = XAgent(settings=settings)
        
        # Test planner has create_plan method
        assert hasattr(agent.planner, "create_plan")
        assert callable(agent.planner.create_plan)
    
    async def test_legacy_planner_returns_plan(self):
        """Test legacy planner can create a plan."""
        settings = Settings(use_langgraph_planner=False)
        agent = XAgent(settings=settings)
        
        # Create a test context
        goal = agent.goal_engine.create_goal(
            description="Write a Python function",
            mode=GoalMode.GOAL_ORIENTED,
            priority=5
        )
        
        context = {
            "active_goal": goal.to_dict(),
            "memory_context": {"recent_actions": []},
        }
        
        # Create plan
        plan = await agent.planner.create_plan(context)
        
        # Legacy planner should return a dict with plan structure
        assert plan is not None
        assert isinstance(plan, dict)
    
    async def test_langgraph_planner_returns_plan(self):
        """Test LangGraph planner can create a plan."""
        settings = Settings(use_langgraph_planner=True)
        agent = XAgent(settings=settings)
        
        # Create a test context
        goal = agent.goal_engine.create_goal(
            description="Write a Python function to calculate factorial",
            mode=GoalMode.GOAL_ORIENTED,
            priority=5,
            completion_criteria=["Function is implemented", "Function is tested"]
        )
        
        context = {
            "active_goal": goal.to_dict(),
            "memory_context": {"recent_actions": []},
        }
        
        # Create plan
        plan = await agent.planner.create_plan(context)
        
        # LangGraph planner should return a dict with plan structure
        assert plan is not None
        assert isinstance(plan, dict)
        # Check for expected fields from LangGraph planner
        assert "type" in plan
        assert "action" in plan
        assert "goal_id" in plan
        assert "goal_complexity" in plan
    
    async def test_agent_can_switch_planners_via_config(self):
        """Test that agent respects configuration for planner selection."""
        # Test with legacy
        settings_legacy = Settings(use_langgraph_planner=False)
        agent_legacy = XAgent(settings=settings_legacy)
        assert agent_legacy.planner.__class__.__name__ == "Planner"
        
        # Test with LangGraph
        settings_langgraph = Settings(use_langgraph_planner=True)
        agent_langgraph = XAgent(settings=settings_langgraph)
        assert agent_langgraph.planner.__class__.__name__ == "LangGraphPlanner"
    
    async def test_default_agent_uses_legacy_planner(self):
        """Test that agent defaults to legacy planner when no config provided."""
        agent = XAgent()
        
        # Should default to legacy planner (use_langgraph_planner=False is default)
        assert agent.planner.__class__.__name__ == "Planner"
        assert not agent.settings.use_langgraph_planner
