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


def test_get_goal_nonexistent():
    """Test getting a nonexistent goal."""
    engine = GoalEngine()

    result = engine.get_goal("nonexistent_id")
    assert result is None


def test_update_goal_status_nonexistent():
    """Test updating status of nonexistent goal."""
    engine = GoalEngine()

    # Should not raise exception
    engine.update_goal_status("nonexistent_id", GoalStatus.COMPLETED)

    # Verify nothing was created
    assert len(engine.goals) == 0


def test_set_active_goal_nonexistent():
    """Test setting nonexistent goal as active."""
    engine = GoalEngine()

    # Should not raise exception
    engine.set_active_goal("nonexistent_id")

    # Active goal should still be None
    assert engine.active_goal_id is None


def test_get_active_goal_none_set():
    """Test getting active goal when none is set."""
    engine = GoalEngine()

    result = engine.get_active_goal()
    assert result is None


def test_check_goal_completion_nonexistent():
    """Test checking completion of nonexistent goal."""
    engine = GoalEngine()

    result = engine.check_goal_completion("nonexistent_id")
    assert result is False


def test_check_goal_completion_with_subgoals():
    """Test checking completion with incomplete subgoals."""
    engine = GoalEngine()

    parent = engine.create_goal(description="Parent")
    child1 = engine.create_goal(description="Child 1", parent_id=parent.id)
    child2 = engine.create_goal(description="Child 2", parent_id=parent.id)

    # Parent not complete if children pending
    assert not engine.check_goal_completion(parent.id)

    # Complete first child
    engine.update_goal_status(child1.id, GoalStatus.COMPLETED)
    assert not engine.check_goal_completion(parent.id)

    # Complete second child
    engine.update_goal_status(child2.id, GoalStatus.COMPLETED)
    assert engine.check_goal_completion(parent.id)


def test_get_goal_hierarchy_nonexistent():
    """Test getting hierarchy of nonexistent goal."""
    engine = GoalEngine()

    result = engine.get_goal_hierarchy("nonexistent_id")
    assert result == {}


def test_list_goals_with_mode_filter():
    """Test listing goals filtered by mode."""
    engine = GoalEngine()

    goal1 = engine.create_goal(description="Goal 1", mode=GoalMode.GOAL_ORIENTED)
    goal2 = engine.create_goal(description="Goal 2", mode=GoalMode.CONTINUOUS)
    goal3 = engine.create_goal(description="Goal 3", mode=GoalMode.GOAL_ORIENTED)

    # Filter by GOAL_ORIENTED mode
    oriented = engine.list_goals(mode=GoalMode.GOAL_ORIENTED)
    assert len(oriented) == 2

    # Filter by CONTINUOUS mode
    continuous = engine.list_goals(mode=GoalMode.CONTINUOUS)
    assert len(continuous) == 1
    assert continuous[0].id == goal2.id


def test_list_goals_with_status_and_mode_filter():
    """Test listing goals with both filters."""
    engine = GoalEngine()

    goal1 = engine.create_goal(description="G1", mode=GoalMode.GOAL_ORIENTED)
    goal2 = engine.create_goal(description="G2", mode=GoalMode.CONTINUOUS)
    goal3 = engine.create_goal(description="G3", mode=GoalMode.GOAL_ORIENTED)

    engine.update_goal_status(goal1.id, GoalStatus.COMPLETED)

    # Filter by GOAL_ORIENTED and COMPLETED
    result = engine.list_goals(status=GoalStatus.COMPLETED, mode=GoalMode.GOAL_ORIENTED)
    assert len(result) == 1
    assert result[0].id == goal1.id


def test_goal_to_dict():
    """Test goal to_dict conversion."""
    engine = GoalEngine()

    goal = engine.create_goal(
        description="Test goal",
        mode=GoalMode.GOAL_ORIENTED,
        priority=5,
        completion_criteria=["criterion1"],
        metadata={"key": "value"},
    )

    goal_dict = goal.to_dict()

    assert goal_dict["id"] == goal.id
    assert goal_dict["description"] == "Test goal"
    assert goal_dict["mode"] == "goal_oriented"
    assert goal_dict["priority"] == 5
    assert "criterion1" in goal_dict["completion_criteria"]
    assert goal_dict["metadata"]["key"] == "value"
    assert "created_at" in goal_dict
    assert "updated_at" in goal_dict
