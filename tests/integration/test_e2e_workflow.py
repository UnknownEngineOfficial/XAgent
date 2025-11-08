"""
End-to-End workflow tests for X-Agent.

Tests complete goal management workflows from creation to completion.
"""

import pytest

from xagent.core.goal_engine import GoalEngine, GoalMode, GoalStatus
from xagent.core.metacognition import MetaCognitionMonitor


@pytest.fixture
def goal_engine():
    """Create a goal engine for testing."""
    return GoalEngine()


@pytest.fixture
def metacognition():
    """Create a metacognition monitor for testing."""
    return MetaCognitionMonitor()


def test_basic_goal_lifecycle(goal_engine):
    """Test the complete lifecycle of a simple goal."""
    # Create a goal
    goal = goal_engine.create_goal(
        description="Write a hello world program",
        mode=GoalMode.GOAL_ORIENTED,
        priority=5,
        completion_criteria=["Code is written", "Code runs successfully"]
    )
    
    # Verify goal was created
    assert goal is not None
    assert goal.description == "Write a hello world program"
    assert goal.status == GoalStatus.PENDING
    assert goal.mode == GoalMode.GOAL_ORIENTED
    
    # List goals
    goals = goal_engine.list_goals()
    assert len(goals) >= 1
    assert any(g.id == goal.id for g in goals)
    
    # Get specific goal
    retrieved_goal = goal_engine.get_goal(goal.id)
    assert retrieved_goal is not None
    assert retrieved_goal.id == goal.id
    assert retrieved_goal.description == goal.description
    
    # Update goal status
    goal_engine.update_goal_status(goal.id, GoalStatus.IN_PROGRESS)
    updated_goal = goal_engine.get_goal(goal.id)
    assert updated_goal.status == GoalStatus.IN_PROGRESS
    
    # Complete the goal
    goal_engine.update_goal_status(goal.id, GoalStatus.COMPLETED)
    completed_goal = goal_engine.get_goal(goal.id)
    assert completed_goal.status == GoalStatus.COMPLETED


def test_hierarchical_goal_workflow(goal_engine):
    """Test workflow with parent and child goals."""
    # Create parent goal
    parent_goal = goal_engine.create_goal(
        description="Build a web application",
        mode=GoalMode.GOAL_ORIENTED,
        priority=8,
        completion_criteria=["Frontend complete", "Backend complete", "Tests pass"]
    )
    
    assert parent_goal is not None
    
    # Create child goals
    child_goal_1 = goal_engine.create_goal(
        description="Build REST API",
        mode=GoalMode.GOAL_ORIENTED,
        priority=7,
        parent_id=parent_goal.id
    )
    
    child_goal_2 = goal_engine.create_goal(
        description="Build React frontend",
        mode=GoalMode.GOAL_ORIENTED,
        priority=7,
        parent_id=parent_goal.id
    )
    
    # Verify hierarchy
    assert child_goal_1.parent_id == parent_goal.id
    assert child_goal_2.parent_id == parent_goal.id
    
    # Get goal hierarchy
    hierarchy = goal_engine.get_goal_hierarchy(parent_goal.id)
    assert hierarchy is not None
    assert hierarchy["goal"]["id"] == parent_goal.id
    assert "sub_goals" in hierarchy
    assert len(hierarchy["sub_goals"]) == 2
    
    # Complete child goals
    goal_engine.update_goal_status(child_goal_1.id, GoalStatus.COMPLETED)
    goal_engine.update_goal_status(child_goal_2.id, GoalStatus.COMPLETED)
    
    # Parent goal should still be manageable
    parent = goal_engine.get_goal(parent_goal.id)
    assert parent is not None


def test_continuous_mode_goal(goal_engine):
    """Test continuous mode goal that runs indefinitely."""
    # Create a continuous goal
    goal = goal_engine.create_goal(
        description="Monitor system health",
        mode=GoalMode.CONTINUOUS,
        priority=3,
        completion_criteria=[]  # No completion criteria for continuous mode
    )
    
    # Verify goal was created in continuous mode
    assert goal is not None
    assert goal.mode == GoalMode.CONTINUOUS
    assert goal.status == GoalStatus.PENDING
    
    # Start processing the goal
    goal_engine.update_goal_status(goal.id, GoalStatus.IN_PROGRESS)
    
    # Continuous goals should stay in progress
    retrieved = goal_engine.get_goal(goal.id)
    assert retrieved.status == GoalStatus.IN_PROGRESS
    
    # Can still be stopped manually
    goal_engine.update_goal_status(goal.id, GoalStatus.COMPLETED)
    stopped = goal_engine.get_goal(goal.id)
    assert stopped.status == GoalStatus.COMPLETED


def test_multiple_goals_priority_order(goal_engine):
    """Test that multiple goals are handled according to priority."""
    # Create goals with different priorities
    goal_low = goal_engine.create_goal(
        description="Low priority task",
        mode=GoalMode.GOAL_ORIENTED,
        priority=2
    )
    
    goal_medium = goal_engine.create_goal(
        description="Medium priority task",
        mode=GoalMode.GOAL_ORIENTED,
        priority=5
    )
    
    goal_high = goal_engine.create_goal(
        description="High priority task",
        mode=GoalMode.GOAL_ORIENTED,
        priority=9
    )
    
    # Verify all goals were created
    assert goal_low is not None
    assert goal_medium is not None
    assert goal_high is not None
    
    # Verify priorities
    assert goal_low.priority == 2
    assert goal_medium.priority == 5
    assert goal_high.priority == 9
    
    # Get next goal (should be highest priority)
    next_goal = goal_engine.get_next_goal()
    
    # Verify we get a goal (it should prioritize by priority)
    assert next_goal is not None
    # Should be the highest priority pending goal
    assert next_goal.priority == 9


def test_goal_error_handling(goal_engine):
    """Test error handling in goal operations."""
    # Try to get non-existent goal
    non_existent = goal_engine.get_goal("non-existent-id")
    assert non_existent is None
    
    # Try to get hierarchy of non-existent goal
    hierarchy = goal_engine.get_goal_hierarchy("non-existent-id")
    assert hierarchy is not None
    assert hierarchy == {}
    
    # Create valid goal
    goal = goal_engine.create_goal(
        description="Valid goal",
        mode=GoalMode.GOAL_ORIENTED
    )
    
    # Try to update non-existent goal status (should not raise error)
    goal_engine.update_goal_status("non-existent-id", GoalStatus.COMPLETED)
    
    # Valid goal should still be unchanged
    retrieved = goal_engine.get_goal(goal.id)
    assert retrieved.status == GoalStatus.PENDING


def test_metacognition_tracking(metacognition):
    """Test that metacognition tracks agent performance."""
    # Evaluate some results
    result1 = {"success": True, "duration": 0.5, "action": "test_action"}
    result2 = {"success": True, "duration": 0.3, "action": "test_action"}
    result3 = {"success": False, "duration": 1.0, "action": "test_action", "error": "Test error"}
    
    metacognition.evaluate(result1)
    metacognition.evaluate(result2)
    metacognition.evaluate(result3)
    
    # Get performance summary
    summary = metacognition.get_performance_summary()
    
    # Verify metrics are tracked
    assert summary is not None
    assert "success_rate" in summary
    assert "total_actions" in summary
    
    # Success rate should be 2/3 (66.67%)
    assert summary["total_actions"] == 3
    assert 0.6 < summary["success_rate"] < 0.7


def test_goal_status_transitions(goal_engine):
    """Test all possible goal status transitions."""
    goal = goal_engine.create_goal(
        description="Test goal status transitions",
        mode=GoalMode.GOAL_ORIENTED
    )
    
    # Initial state
    assert goal.status == GoalStatus.PENDING
    
    # Pending -> In Progress
    goal_engine.update_goal_status(goal.id, GoalStatus.IN_PROGRESS)
    assert goal_engine.get_goal(goal.id).status == GoalStatus.IN_PROGRESS
    
    # In Progress -> Completed
    goal_engine.update_goal_status(goal.id, GoalStatus.COMPLETED)
    assert goal_engine.get_goal(goal.id).status == GoalStatus.COMPLETED


def test_goal_completion_criteria(goal_engine):
    """Test goals with completion criteria."""
    criteria = [
        "All tests pass",
        "Code review approved",
        "Documentation updated"
    ]
    
    goal = goal_engine.create_goal(
        description="Implement feature X",
        mode=GoalMode.GOAL_ORIENTED,
        priority=7,
        completion_criteria=criteria
    )
    
    # Verify criteria were stored
    assert goal.completion_criteria == criteria
    assert len(goal.completion_criteria) == 3
    
    # Retrieved goal should have same criteria
    retrieved = goal_engine.get_goal(goal.id)
    assert retrieved.completion_criteria == criteria


def test_multiple_goal_engines_independent(goal_engine):
    """Test that multiple goal engines maintain independent state."""
    # Create goal in first engine
    goal1 = goal_engine.create_goal(
        description="Goal in engine 1",
        mode=GoalMode.GOAL_ORIENTED
    )
    
    # Create second engine
    engine2 = GoalEngine()
    
    # Create goal in second engine
    goal2 = engine2.create_goal(
        description="Goal in engine 2",
        mode=GoalMode.GOAL_ORIENTED
    )
    
    # Each engine should only have its own goal
    assert len(goal_engine.list_goals()) >= 1
    assert len(engine2.list_goals()) == 1
    
    # Goals should have different IDs
    assert goal1.id != goal2.id
    
    # Each engine should only find its own goal
    assert goal_engine.get_goal(goal2.id) is None
    assert engine2.get_goal(goal1.id) is None
