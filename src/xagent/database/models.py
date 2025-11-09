"""Database models for X-Agent."""

from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class GoalStatus(PyEnum):
    """Goal status enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class GoalMode(PyEnum):
    """Goal mode enumeration."""

    ONE_TIME = "one_time"
    CONTINUOUS = "continuous"


class Goal(Base):
    """Goal model for persistent storage."""

    __tablename__ = "goals"

    id = Column(String, primary_key=True, index=True)
    description = Column(Text, nullable=False)
    status = Column(Enum(GoalStatus), default=GoalStatus.PENDING, nullable=False)
    mode = Column(Enum(GoalMode), default=GoalMode.ONE_TIME, nullable=False)
    priority = Column(Integer, default=5, nullable=False)
    parent_id = Column(String, ForeignKey("goals.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)

    # Relationships
    parent = relationship("Goal", remote_side=[id], backref="children")


class AgentState(Base):
    """Agent state model for persistent storage."""

    __tablename__ = "agent_states"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String, unique=True, nullable=False, index=True)
    is_running = Column(Boolean, default=False, nullable=False)
    current_goal_id = Column(String, ForeignKey("goals.id"), nullable=True)
    mode = Column(String, default="idle", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)

    # Relationships
    current_goal = relationship("Goal")


class Memory(Base):
    """Memory model for persistent storage."""

    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String, nullable=False, index=True)
    memory_type = Column(String, nullable=False, index=True)  # short, medium, long
    content = Column(Text, nullable=False)
    embedding_id = Column(String, nullable=True, index=True)  # Reference to vector DB
    importance = Column(Float, default=0.5, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    accessed_at = Column(DateTime, default=utc_now, nullable=False)
    access_count = Column(Integer, default=0, nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)


class Action(Base):
    """Action execution history model."""

    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String, nullable=False, index=True)
    goal_id = Column(String, ForeignKey("goals.id"), nullable=True)
    action_type = Column(String, nullable=False)
    action_data = Column(JSON, nullable=False)
    result = Column(JSON, nullable=True)
    success = Column(Boolean, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, default=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # Relationships
    goal = relationship("Goal")


class MetricSnapshot(Base):
    """Metric snapshot for performance tracking."""

    __tablename__ = "metric_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String, nullable=False, index=True)
    metric_type = Column(String, nullable=False, index=True)
    metric_name = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)
    metadata_ = Column("metadata", JSON, nullable=True)
