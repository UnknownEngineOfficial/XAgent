"""Tests for goal engine."""

import pytest
from xagent.core.goal_engine import GoalEngine, GoalMode, GoalStatus


def test_create_goal():
    """Test goal creation."""
    engine = GoalEngine()
    
    goal = engine.create_goal(
        description="Test goal",
        mode=GoalMode.GOAL_ORIENTED,
        priority=5,
    )
    
    assert goal.id is not None
    assert goal.description == "Test goal"
    assert goal.mode == GoalMode.GOAL_ORIENTED
    assert goal.priority == 5
    assert goal.status == GoalStatus.PENDING


def test_goal_hierarchy():
    """Test goal hierarchy."""
    engine = GoalEngine()
    
    # Create parent goal
    parent = engine.create_goal(
        description="Parent goal",
        priority=10,
    )
    
    # Create sub-goal
    child = engine.create_goal(
        description="Child goal",
        parent_id=parent.id,
        priority=5,
    )
    
    # Check hierarchy
    assert child.parent_id == parent.id
    assert child.id in parent.sub_goals
    
    # Get hierarchy
    hierarchy = engine.get_goal_hierarchy(parent.id)
    assert hierarchy["goal"]["id"] == parent.id
    assert len(hierarchy["sub_goals"]) == 1
    assert hierarchy["sub_goals"][0]["goal"]["id"] == child.id


def test_goal_status_updates():
    """Test goal status updates."""
    engine = GoalEngine()
    
    goal = engine.create_goal(description="Test goal")
    
    # Set active
    engine.set_active_goal(goal.id)
    assert engine.get_active_goal().id == goal.id
    assert goal.status == GoalStatus.IN_PROGRESS
    
    # Complete goal
    engine.update_goal_status(goal.id, GoalStatus.COMPLETED)
    assert goal.status == GoalStatus.COMPLETED
    assert goal.completed_at is not None


def test_get_next_goal():
    """Test getting next goal by priority."""
    engine = GoalEngine()
    
    # Create goals with different priorities
    goal1 = engine.create_goal(description="Low priority", priority=1)
    goal2 = engine.create_goal(description="High priority", priority=10)
    goal3 = engine.create_goal(description="Medium priority", priority=5)
    
    # Get next goal (should be highest priority)
    next_goal = engine.get_next_goal()
    assert next_goal.id == goal2.id


def test_continuous_goal():
    """Test continuous goal never completes."""
    engine = GoalEngine()
    
    goal = engine.create_goal(
        description="Continuous task",
        mode=GoalMode.CONTINUOUS,
    )
    
    # Continuous goals should never be considered complete
    assert not engine.check_goal_completion(goal.id)
    
    # Even if marked completed, check should return False
    engine.update_goal_status(goal.id, GoalStatus.COMPLETED)
    assert not engine.check_goal_completion(goal.id)


def test_list_goals_with_filters():
    """Test listing goals with status filter."""
    engine = GoalEngine()
    
    goal1 = engine.create_goal(description="Goal 1")
    goal2 = engine.create_goal(description="Goal 2")
    goal3 = engine.create_goal(description="Goal 3")
    
    engine.update_goal_status(goal2.id, GoalStatus.COMPLETED)
    
    # List all goals
    all_goals = engine.list_goals()
    assert len(all_goals) == 3
    
    # List only pending
    pending = engine.list_goals(status=GoalStatus.PENDING)
    assert len(pending) == 2
    
    # List only completed
    completed = engine.list_goals(status=GoalStatus.COMPLETED)
    assert len(completed) == 1
    assert completed[0].id == goal2.id
