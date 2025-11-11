"""Property-based tests for Goal Engine using Hypothesis.

These tests use fuzzing to explore edge cases and ensure robustness
of the goal management system under various inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime, timezone

from xagent.core.goal_engine import Goal, GoalEngine, GoalMode, GoalStatus


# Custom strategies for our domain
@st.composite
def goal_descriptions(draw):
    """Generate valid goal descriptions."""
    # Mix of normal strings and edge cases
    return draw(
        st.one_of(
            st.text(min_size=1, max_size=1000),
            st.text(alphabet=st.characters(blacklist_categories=("Cs", "Cc")), min_size=1, max_size=100),
            st.from_regex(r"[a-zA-Z0-9 ]{1,200}", fullmatch=True),
        )
    )


@st.composite
def priorities(draw):
    """Generate priority values including edge cases."""
    return draw(
        st.one_of(
            st.integers(min_value=-1000, max_value=1000),
            st.just(0),
            st.just(-1),
            st.just(999999),
        )
    )


@st.composite
def goal_ids(draw):
    """Generate valid and invalid goal IDs."""
    return draw(
        st.one_of(
            st.text(min_size=1, max_size=100),
            st.from_regex(r"goal_[a-f0-9\-]{10,50}", fullmatch=True),
            st.just(""),
        )
    )


class TestGoalEngineProperties:
    """Property-based tests for GoalEngine."""

    @given(
        description=goal_descriptions(),
        mode=st.sampled_from(GoalMode),
        priority=priorities(),
    )
    @settings(max_examples=1000, suppress_health_check=[HealthCheck.too_slow])
    def test_create_goal_always_returns_valid_goal(self, description, mode, priority):
        """Property: Creating a goal always returns a valid Goal object."""
        engine = GoalEngine()
        
        goal = engine.create_goal(
            description=description,
            mode=mode,
            priority=priority,
        )
        
        # Invariants that must always hold
        assert isinstance(goal, Goal)
        assert goal.id is not None
        assert goal.id != ""
        assert goal.description == description
        assert goal.mode == mode
        assert goal.priority == priority
        assert goal.status == GoalStatus.PENDING
        assert isinstance(goal.created_at, datetime)
        assert isinstance(goal.updated_at, datetime)
        assert goal.created_at <= goal.updated_at
        
        # Goal should be stored in engine
        assert goal.id in engine.goals
        assert engine.goals[goal.id] == goal

    @given(
        description=goal_descriptions(),
        priority=priorities(),
    )
    @settings(max_examples=1000)
    def test_goal_id_uniqueness(self, description, priority):
        """Property: Each created goal has a unique ID."""
        engine = GoalEngine()
        
        # Create multiple goals
        goal1 = engine.create_goal(description=description, priority=priority)
        goal2 = engine.create_goal(description=description, priority=priority)
        goal3 = engine.create_goal(description=description, priority=priority)
        
        # IDs must be unique
        ids = {goal1.id, goal2.id, goal3.id}
        assert len(ids) == 3, "Goal IDs must be unique"

    @given(
        description=goal_descriptions(),
        num_goals=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=500)
    def test_list_goals_returns_all_created_goals(self, description, num_goals):
        """Property: list_goals returns exactly the goals that were created."""
        engine = GoalEngine()
        
        created_ids = set()
        for i in range(num_goals):
            goal = engine.create_goal(description=f"{description}_{i}")
            created_ids.add(goal.id)
        
        all_goals = engine.list_goals()
        retrieved_ids = {g.id for g in all_goals}
        
        assert created_ids == retrieved_ids
        assert len(all_goals) == num_goals

    @given(
        description=goal_descriptions(),
        status=st.sampled_from(GoalStatus),
    )
    @settings(max_examples=1000)
    def test_update_status_is_idempotent(self, description, status):
        """Property: Updating status multiple times with same value is idempotent."""
        engine = GoalEngine()
        goal = engine.create_goal(description=description)
        
        # Update status multiple times (method returns None)
        engine.update_goal_status(goal.id, status)
        engine.update_goal_status(goal.id, status)
        engine.update_goal_status(goal.id, status)
        
        # Verify status was updated
        retrieved_goal = engine.get_goal(goal.id)
        assert retrieved_goal is not None
        assert retrieved_goal.status == status

    @given(
        parent_description=goal_descriptions(),
        child_description=goal_descriptions(),
        num_children=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=500)
    def test_parent_child_relationship_consistency(
        self, parent_description, child_description, num_children
    ):
        """Property: Parent-child relationships are always consistent."""
        engine = GoalEngine()
        
        # Create parent
        parent = engine.create_goal(description=parent_description)
        
        # Create children
        child_ids = []
        for i in range(num_children):
            child = engine.create_goal(
                description=f"{child_description}_{i}",
                parent_id=parent.id,
            )
            child_ids.append(child.id)
        
        # Check parent's sub_goals list
        parent_goal = engine.get_goal(parent.id)
        assert parent_goal is not None
        assert len(parent_goal.sub_goals) == num_children
        assert set(parent_goal.sub_goals) == set(child_ids)
        
        # Check each child's parent_id
        for child_id in child_ids:
            child_goal = engine.get_goal(child_id)
            assert child_goal is not None
            assert child_goal.parent_id == parent.id

    @given(
        description=goal_descriptions(),
    )
    @settings(max_examples=1000)
    def test_goal_stored_and_retrievable(self, description):
        """Property: Created goals are stored and can be retrieved."""
        engine = GoalEngine()
        goal = engine.create_goal(description=description)
        goal_id = goal.id
        
        # Verify goal exists
        assert goal_id in engine.goals
        assert engine.get_goal(goal_id) is not None
        
        # Verify retrieved goal matches created goal
        retrieved = engine.get_goal(goal_id)
        assert retrieved.id == goal.id
        assert retrieved.description == goal.description

    @given(
        descriptions=st.lists(goal_descriptions(), min_size=1, max_size=50),
        priorities=st.lists(priorities(), min_size=1, max_size=50),
    )
    @settings(max_examples=500)
    def test_list_goals_by_status_returns_correct_subset(self, descriptions, priorities):
        """Property: Filtering by status returns only goals with that status."""
        engine = GoalEngine()
        
        # Ensure lists have same length
        n = min(len(descriptions), len(priorities))
        descriptions = descriptions[:n]
        priorities = priorities[:n]
        
        # Create goals with various statuses
        pending_ids = set()
        in_progress_ids = set()
        
        for i, (desc, prio) in enumerate(zip(descriptions, priorities)):
            goal = engine.create_goal(description=desc, priority=prio)
            
            if i % 2 == 0:
                # Leave as PENDING
                pending_ids.add(goal.id)
            else:
                # Set to IN_PROGRESS
                engine.update_goal_status(goal.id, GoalStatus.IN_PROGRESS)
                in_progress_ids.add(goal.id)
        
        # Filter by status
        pending_goals = engine.list_goals(status=GoalStatus.PENDING)
        in_progress_goals = engine.list_goals(status=GoalStatus.IN_PROGRESS)
        
        # Verify correct filtering
        assert set(g.id for g in pending_goals) == pending_ids
        assert set(g.id for g in in_progress_goals) == in_progress_ids
        
        # All returned goals should have correct status
        assert all(g.status == GoalStatus.PENDING for g in pending_goals)
        assert all(g.status == GoalStatus.IN_PROGRESS for g in in_progress_goals)

    @given(
        description=goal_descriptions(),
        completion_criteria=st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=10),
    )
    @settings(max_examples=1000)
    def test_completion_criteria_preserved(self, description, completion_criteria):
        """Property: Completion criteria are preserved exactly as provided."""
        engine = GoalEngine()
        
        goal = engine.create_goal(
            description=description,
            completion_criteria=completion_criteria,
        )
        
        # Retrieve and verify
        retrieved = engine.get_goal(goal.id)
        assert retrieved is not None
        assert retrieved.completion_criteria == completion_criteria
        assert len(retrieved.completion_criteria) == len(completion_criteria)

    @given(
        description=goal_descriptions(),
        metadata=st.dictionaries(
            keys=st.text(min_size=1, max_size=50),
            values=st.one_of(
                st.text(),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.booleans(),
                st.none(),
            ),
            min_size=0,
            max_size=20,
        ),
    )
    @settings(max_examples=1000)
    def test_metadata_preserved(self, description, metadata):
        """Property: Goal metadata is preserved exactly as provided."""
        engine = GoalEngine()
        
        goal = engine.create_goal(
            description=description,
            metadata=metadata,
        )
        
        # Retrieve and verify
        retrieved = engine.get_goal(goal.id)
        assert retrieved is not None
        assert retrieved.metadata == metadata

    @given(
        description=goal_descriptions(),
    )
    @settings(max_examples=1000)
    def test_to_dict_is_reversible(self, description):
        """Property: Goal.to_dict() produces a dictionary with all essential fields."""
        engine = GoalEngine()
        goal = engine.create_goal(description=description)
        
        goal_dict = goal.to_dict()
        
        # Check all required fields are present
        required_fields = [
            "id", "description", "mode", "status", "priority",
            "parent_id", "sub_goals", "completion_criteria",
            "created_at", "updated_at", "completed_at", "metadata"
        ]
        
        for field in required_fields:
            assert field in goal_dict
        
        # Check types
        assert isinstance(goal_dict["id"], str)
        assert isinstance(goal_dict["description"], str)
        assert isinstance(goal_dict["mode"], str)
        assert isinstance(goal_dict["status"], str)
        assert isinstance(goal_dict["priority"], int)
        assert isinstance(goal_dict["sub_goals"], list)
        assert isinstance(goal_dict["completion_criteria"], list)
        assert isinstance(goal_dict["metadata"], dict)

    @given(
        num_operations=st.integers(min_value=10, max_value=100),
    )
    @settings(max_examples=100)
    def test_mixed_operations_maintain_consistency(self, num_operations):
        """Property: Mixed CRUD operations maintain engine consistency."""
        engine = GoalEngine()
        created_ids = set()
        
        for i in range(num_operations):
            operation = i % 3
            
            if operation == 0:  # Create
                goal = engine.create_goal(description=f"Goal {i}")
                created_ids.add(goal.id)
                
            elif operation == 1 and created_ids:  # Update status
                goal_id = list(created_ids)[i % len(created_ids)]
                engine.update_goal_status(goal_id, GoalStatus.IN_PROGRESS)
                    
            elif operation == 2 and created_ids:  # Get
                goal_id = list(created_ids)[i % len(created_ids)]
                goal = engine.get_goal(goal_id)
                assert goal is not None
        
        # Verify consistency
        all_goals = engine.list_goals()
        assert len(all_goals) == len(created_ids)
        
        # All created goals should be retrievable
        for goal in all_goals:
            assert goal.id in created_ids
            retrieved = engine.get_goal(goal.id)
            assert retrieved is not None


class TestGoalProperties:
    """Property-based tests for Goal dataclass."""

    @given(
        description=goal_descriptions(),
        mode=st.sampled_from(GoalMode),
        status=st.sampled_from(GoalStatus),
        priority=priorities(),
    )
    @settings(max_examples=1000)
    def test_goal_creation_with_valid_inputs(self, description, mode, status, priority):
        """Property: Goal can be created with any valid combination of inputs."""
        goal = Goal(
            description=description,
            mode=mode,
            status=status,
            priority=priority,
        )
        
        assert goal.description == description
        assert goal.mode == mode
        assert goal.status == status
        assert goal.priority == priority
        assert isinstance(goal.id, str)
        assert goal.id != ""
        assert isinstance(goal.created_at, datetime)
        assert isinstance(goal.updated_at, datetime)

    @given(
        goal_data=st.fixed_dictionaries({
            "description": goal_descriptions(),
            "mode": st.sampled_from(GoalMode),
            "status": st.sampled_from(GoalStatus),
            "priority": priorities(),
            "sub_goals": st.lists(st.text(min_size=1, max_size=50), max_size=10),
            "completion_criteria": st.lists(st.text(min_size=1, max_size=100), max_size=5),
        })
    )
    @settings(max_examples=500)
    def test_goal_to_dict_contains_all_data(self, goal_data):
        """Property: to_dict() preserves all goal data."""
        goal = Goal(**goal_data)
        goal_dict = goal.to_dict()
        
        # Original data should be preserved
        assert goal_dict["description"] == goal_data["description"]
        assert goal_dict["mode"] == goal_data["mode"].value
        assert goal_dict["status"] == goal_data["status"].value
        assert goal_dict["priority"] == goal_data["priority"]
        assert goal_dict["sub_goals"] == goal_data["sub_goals"]
        assert goal_dict["completion_criteria"] == goal_data["completion_criteria"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
