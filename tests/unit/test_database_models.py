"""Tests for database models."""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from xagent.database.models import (
    Base,
    Goal,
    GoalStatus,
    GoalMode,
    AgentState,
    Memory,
    Action,
    MetricSnapshot,
)


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestGoalModel:
    """Tests for Goal model."""

    def test_create_goal(self, db_session):
        """Test creating a goal."""
        goal = Goal(
            id="test-goal-1",
            description="Test goal",
            status=GoalStatus.PENDING,
            mode=GoalMode.ONE_TIME,
            priority=5,
        )
        db_session.add(goal)
        db_session.commit()

        retrieved = db_session.query(Goal).filter_by(id="test-goal-1").first()
        assert retrieved is not None
        assert retrieved.description == "Test goal"
        assert retrieved.status == GoalStatus.PENDING
        assert retrieved.mode == GoalMode.ONE_TIME
        assert retrieved.priority == 5

    def test_goal_with_parent(self, db_session):
        """Test goal with parent relationship."""
        parent = Goal(
            id="parent-goal",
            description="Parent goal",
            status=GoalStatus.IN_PROGRESS,
        )
        child = Goal(
            id="child-goal",
            description="Child goal",
            parent_id="parent-goal",
        )
        db_session.add(parent)
        db_session.add(child)
        db_session.commit()

        retrieved_child = db_session.query(Goal).filter_by(id="child-goal").first()
        assert retrieved_child.parent is not None
        assert retrieved_child.parent.id == "parent-goal"
        assert retrieved_child.parent.description == "Parent goal"

        retrieved_parent = db_session.query(Goal).filter_by(id="parent-goal").first()
        assert len(retrieved_parent.children) == 1
        assert retrieved_parent.children[0].id == "child-goal"

    def test_goal_default_values(self, db_session):
        """Test goal default values."""
        goal = Goal(id="test-goal-2", description="Test goal with defaults")
        db_session.add(goal)
        db_session.commit()

        retrieved = db_session.query(Goal).filter_by(id="test-goal-2").first()
        assert retrieved.status == GoalStatus.PENDING
        assert retrieved.mode == GoalMode.ONE_TIME
        assert retrieved.priority == 5
        assert retrieved.created_at is not None
        assert retrieved.updated_at is not None
        assert retrieved.completed_at is None

    def test_goal_statuses(self, db_session):
        """Test all goal statuses."""
        statuses = [
            GoalStatus.PENDING,
            GoalStatus.IN_PROGRESS,
            GoalStatus.COMPLETED,
            GoalStatus.FAILED,
            GoalStatus.BLOCKED,
        ]

        for i, status in enumerate(statuses):
            goal = Goal(
                id=f"goal-{i}",
                description=f"Goal with status {status.value}",
                status=status,
            )
            db_session.add(goal)

        db_session.commit()

        for i, status in enumerate(statuses):
            retrieved = db_session.query(Goal).filter_by(id=f"goal-{i}").first()
            assert retrieved.status == status

    def test_goal_modes(self, db_session):
        """Test goal modes."""
        one_time = Goal(
            id="goal-one-time",
            description="One-time goal",
            mode=GoalMode.ONE_TIME,
        )
        continuous = Goal(
            id="goal-continuous",
            description="Continuous goal",
            mode=GoalMode.CONTINUOUS,
        )
        db_session.add(one_time)
        db_session.add(continuous)
        db_session.commit()

        retrieved_one_time = db_session.query(Goal).filter_by(id="goal-one-time").first()
        assert retrieved_one_time.mode == GoalMode.ONE_TIME

        retrieved_continuous = (
            db_session.query(Goal).filter_by(id="goal-continuous").first()
        )
        assert retrieved_continuous.mode == GoalMode.CONTINUOUS

    def test_goal_metadata(self, db_session):
        """Test goal metadata storage."""
        metadata = {"key": "value", "number": 42, "nested": {"inner": "data"}}
        goal = Goal(
            id="goal-with-metadata",
            description="Goal with metadata",
            metadata_=metadata,
        )
        db_session.add(goal)
        db_session.commit()

        retrieved = db_session.query(Goal).filter_by(id="goal-with-metadata").first()
        assert retrieved.metadata_ == metadata

    def test_goal_completed_at(self, db_session):
        """Test goal completion timestamp."""
        goal = Goal(
            id="completed-goal",
            description="Completed goal",
            status=GoalStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
        )
        db_session.add(goal)
        db_session.commit()

        retrieved = db_session.query(Goal).filter_by(id="completed-goal").first()
        assert retrieved.completed_at is not None
        assert isinstance(retrieved.completed_at, datetime)


class TestAgentStateModel:
    """Tests for AgentState model."""

    def test_create_agent_state(self, db_session):
        """Test creating agent state."""
        state = AgentState(
            agent_id="agent-1",
            is_running=True,
            mode="active",
        )
        db_session.add(state)
        db_session.commit()

        retrieved = db_session.query(AgentState).filter_by(agent_id="agent-1").first()
        assert retrieved is not None
        assert retrieved.agent_id == "agent-1"
        assert retrieved.is_running is True
        assert retrieved.mode == "active"

    def test_agent_state_with_goal(self, db_session):
        """Test agent state with current goal."""
        goal = Goal(id="current-goal", description="Current goal")
        state = AgentState(
            agent_id="agent-2",
            current_goal_id="current-goal",
        )
        db_session.add(goal)
        db_session.add(state)
        db_session.commit()

        retrieved = db_session.query(AgentState).filter_by(agent_id="agent-2").first()
        assert retrieved.current_goal is not None
        assert retrieved.current_goal.id == "current-goal"

    def test_agent_state_defaults(self, db_session):
        """Test agent state default values."""
        state = AgentState(agent_id="agent-3")
        db_session.add(state)
        db_session.commit()

        retrieved = db_session.query(AgentState).filter_by(agent_id="agent-3").first()
        assert retrieved.is_running is False
        assert retrieved.mode == "idle"
        assert retrieved.created_at is not None
        assert retrieved.updated_at is not None

    def test_agent_state_metadata(self, db_session):
        """Test agent state metadata."""
        metadata = {"config": "value", "settings": {"key": "data"}}
        state = AgentState(agent_id="agent-4", metadata_=metadata)
        db_session.add(state)
        db_session.commit()

        retrieved = db_session.query(AgentState).filter_by(agent_id="agent-4").first()
        assert retrieved.metadata_ == metadata


class TestMemoryModel:
    """Tests for Memory model."""

    def test_create_memory(self, db_session):
        """Test creating a memory."""
        memory = Memory(
            agent_id="agent-1",
            memory_type="short",
            content="Test memory content",
            importance=0.8,
        )
        db_session.add(memory)
        db_session.commit()

        retrieved = db_session.query(Memory).filter_by(agent_id="agent-1").first()
        assert retrieved is not None
        assert retrieved.memory_type == "short"
        assert retrieved.content == "Test memory content"
        assert retrieved.importance == 0.8

    def test_memory_types(self, db_session):
        """Test different memory types."""
        types = ["short", "medium", "long"]

        for i, mem_type in enumerate(types):
            memory = Memory(
                agent_id=f"agent-{i}",
                memory_type=mem_type,
                content=f"Content for {mem_type} memory",
            )
            db_session.add(memory)

        db_session.commit()

        for i, mem_type in enumerate(types):
            retrieved = db_session.query(Memory).filter_by(agent_id=f"agent-{i}").first()
            assert retrieved.memory_type == mem_type

    def test_memory_with_embedding(self, db_session):
        """Test memory with embedding reference."""
        memory = Memory(
            agent_id="agent-2",
            memory_type="long",
            content="Memory with embedding",
            embedding_id="embedding-123",
        )
        db_session.add(memory)
        db_session.commit()

        retrieved = db_session.query(Memory).filter_by(embedding_id="embedding-123").first()
        assert retrieved is not None
        assert retrieved.embedding_id == "embedding-123"

    def test_memory_defaults(self, db_session):
        """Test memory default values."""
        memory = Memory(
            agent_id="agent-3",
            memory_type="medium",
            content="Test content",
        )
        db_session.add(memory)
        db_session.commit()

        retrieved = db_session.query(Memory).filter_by(agent_id="agent-3").first()
        assert retrieved.importance == 0.5
        assert retrieved.access_count == 0
        assert retrieved.created_at is not None
        assert retrieved.accessed_at is not None

    def test_memory_metadata(self, db_session):
        """Test memory metadata."""
        metadata = {"source": "user_input", "tags": ["important", "recent"]}
        memory = Memory(
            agent_id="agent-4",
            memory_type="short",
            content="Memory with metadata",
            metadata_=metadata,
        )
        db_session.add(memory)
        db_session.commit()

        retrieved = db_session.query(Memory).filter_by(agent_id="agent-4").first()
        assert retrieved.metadata_ == metadata


class TestActionModel:
    """Tests for Action model."""

    def test_create_action(self, db_session):
        """Test creating an action."""
        action = Action(
            agent_id="agent-1",
            action_type="tool_call",
            action_data={"tool": "test", "params": {"key": "value"}},
            success=True,
        )
        db_session.add(action)
        db_session.commit()

        retrieved = db_session.query(Action).filter_by(agent_id="agent-1").first()
        assert retrieved is not None
        assert retrieved.action_type == "tool_call"
        assert retrieved.success is True

    def test_action_with_goal(self, db_session):
        """Test action associated with a goal."""
        goal = Goal(id="action-goal", description="Goal for action")
        action = Action(
            agent_id="agent-2",
            goal_id="action-goal",
            action_type="think",
            action_data={"thought": "planning"},
        )
        db_session.add(goal)
        db_session.add(action)
        db_session.commit()

        retrieved = db_session.query(Action).filter_by(agent_id="agent-2").first()
        assert retrieved.goal is not None
        assert retrieved.goal.id == "action-goal"

    def test_action_with_result(self, db_session):
        """Test action with result and error."""
        action_success = Action(
            agent_id="agent-3",
            action_type="execute",
            action_data={"command": "ls"},
            result={"output": "file1.txt\nfile2.txt"},
            success=True,
        )
        action_error = Action(
            agent_id="agent-3",
            action_type="execute",
            action_data={"command": "invalid"},
            success=False,
            error="Command not found",
        )
        db_session.add(action_success)
        db_session.add(action_error)
        db_session.commit()

        actions = db_session.query(Action).filter_by(agent_id="agent-3").all()
        assert len(actions) == 2

        success_action = [a for a in actions if a.success][0]
        assert success_action.result is not None
        assert success_action.error is None

        error_action = [a for a in actions if not a.success][0]
        assert error_action.error == "Command not found"

    def test_action_timing(self, db_session):
        """Test action timing fields."""
        now = datetime.now(timezone.utc)
        action = Action(
            agent_id="agent-4",
            action_type="think",
            action_data={"thought": "test"},
            started_at=now,
            completed_at=now + timedelta(seconds=2),
            duration_ms=2000,
        )
        db_session.add(action)
        db_session.commit()

        retrieved = db_session.query(Action).filter_by(agent_id="agent-4").first()
        assert retrieved.started_at is not None
        assert retrieved.completed_at is not None
        assert retrieved.duration_ms == 2000


class TestMetricSnapshotModel:
    """Tests for MetricSnapshot model."""

    def test_create_metric_snapshot(self, db_session):
        """Test creating a metric snapshot."""
        metric = MetricSnapshot(
            agent_id="agent-1",
            metric_type="performance",
            metric_name="cpu_usage",
            value=45.5,
        )
        db_session.add(metric)
        db_session.commit()

        retrieved = (
            db_session.query(MetricSnapshot).filter_by(agent_id="agent-1").first()
        )
        assert retrieved is not None
        assert retrieved.metric_type == "performance"
        assert retrieved.metric_name == "cpu_usage"
        assert retrieved.value == 45.5

    def test_metric_snapshot_with_metadata(self, db_session):
        """Test metric snapshot with metadata."""
        metadata = {"unit": "percent", "threshold": 80}
        metric = MetricSnapshot(
            agent_id="agent-2",
            metric_type="resource",
            metric_name="memory_usage",
            value=512.0,
            metadata_=metadata,
        )
        db_session.add(metric)
        db_session.commit()

        retrieved = (
            db_session.query(MetricSnapshot).filter_by(agent_id="agent-2").first()
        )
        assert retrieved.metadata_ == metadata

    def test_multiple_metric_snapshots(self, db_session):
        """Test storing multiple metric snapshots over time."""
        for i in range(5):
            metric = MetricSnapshot(
                agent_id="agent-3",
                metric_type="performance",
                metric_name="response_time",
                value=100.0 + i * 10,
                timestamp=datetime.now(timezone.utc) + timedelta(seconds=i),
            )
            db_session.add(metric)

        db_session.commit()

        metrics = db_session.query(MetricSnapshot).filter_by(agent_id="agent-3").all()
        assert len(metrics) == 5

        # Check values are stored correctly
        values = sorted([m.value for m in metrics])
        assert values == [100.0, 110.0, 120.0, 130.0, 140.0]


class TestEnumerations:
    """Tests for enumerations."""

    def test_goal_status_values(self):
        """Test GoalStatus enum values."""
        assert GoalStatus.PENDING.value == "pending"
        assert GoalStatus.IN_PROGRESS.value == "in_progress"
        assert GoalStatus.COMPLETED.value == "completed"
        assert GoalStatus.FAILED.value == "failed"
        assert GoalStatus.BLOCKED.value == "blocked"

    def test_goal_mode_values(self):
        """Test GoalMode enum values."""
        assert GoalMode.ONE_TIME.value == "one_time"
        assert GoalMode.CONTINUOUS.value == "continuous"


class TestRelationships:
    """Tests for model relationships."""

    def test_goal_hierarchy(self, db_session):
        """Test complete goal hierarchy."""
        root = Goal(id="root", description="Root goal")
        child1 = Goal(id="child1", description="Child 1", parent_id="root")
        child2 = Goal(id="child2", description="Child 2", parent_id="root")
        grandchild = Goal(id="grandchild", description="Grandchild", parent_id="child1")

        db_session.add_all([root, child1, child2, grandchild])
        db_session.commit()

        # Test parent-child relationships
        root_retrieved = db_session.query(Goal).filter_by(id="root").first()
        assert len(root_retrieved.children) == 2

        child1_retrieved = db_session.query(Goal).filter_by(id="child1").first()
        assert child1_retrieved.parent.id == "root"
        assert len(child1_retrieved.children) == 1

        grandchild_retrieved = db_session.query(Goal).filter_by(id="grandchild").first()
        assert grandchild_retrieved.parent.id == "child1"

    def test_agent_state_to_goal_relationship(self, db_session):
        """Test agent state to goal relationship."""
        goal = Goal(id="active-goal", description="Active goal")
        state = AgentState(agent_id="agent-rel", current_goal_id="active-goal")

        db_session.add(goal)
        db_session.add(state)
        db_session.commit()

        # Query through relationship
        state_retrieved = db_session.query(AgentState).filter_by(agent_id="agent-rel").first()
        assert state_retrieved.current_goal.description == "Active goal"

    def test_action_to_goal_relationship(self, db_session):
        """Test action to goal relationship."""
        goal = Goal(id="goal-for-action", description="Goal for testing action")
        action = Action(
            agent_id="agent-action",
            goal_id="goal-for-action",
            action_type="test",
            action_data={},
        )

        db_session.add(goal)
        db_session.add(action)
        db_session.commit()

        # Query through relationship
        action_retrieved = (
            db_session.query(Action).filter_by(agent_id="agent-action").first()
        )
        assert action_retrieved.goal.description == "Goal for testing action"
