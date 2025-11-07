"""Goal Engine - Purpose Core for X-Agent."""

from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid


class GoalMode(str, Enum):
    """Goal execution modes."""
    
    GOAL_ORIENTED = "goal_oriented"  # Works until goal is achieved
    CONTINUOUS = "continuous"  # Works continuously without end goal


class GoalStatus(str, Enum):
    """Goal status."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class Goal:
    """Represents a goal or task."""
    
    id: str = field(default_factory=lambda: f"goal_{str(uuid.uuid4())}")
    description: str = ""
    mode: GoalMode = GoalMode.GOAL_ORIENTED
    status: GoalStatus = GoalStatus.PENDING
    priority: int = 0
    parent_id: Optional[str] = None
    sub_goals: List[str] = field(default_factory=list)
    completion_criteria: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert goal to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "mode": self.mode.value,
            "status": self.status.value,
            "priority": self.priority,
            "parent_id": self.parent_id,
            "sub_goals": self.sub_goals,
            "completion_criteria": self.completion_criteria,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }


class GoalEngine:
    """
    Goal Engine (Purpose Core) - Manages goals and tasks.
    
    Supports two modes:
    - Goal-oriented: Works until specific goal is achieved
    - Continuous: Works indefinitely, reacting to events
    """
    
    def __init__(self) -> None:
        """Initialize goal engine."""
        self.goals: Dict[str, Goal] = {}
        self.active_goal_id: Optional[str] = None
        
    def create_goal(
        self,
        description: str,
        mode: GoalMode = GoalMode.GOAL_ORIENTED,
        priority: int = 0,
        parent_id: Optional[str] = None,
        completion_criteria: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Goal:
        """
        Create a new goal.
        
        Args:
            description: Goal description
            mode: Goal mode (goal_oriented or continuous)
            priority: Priority level (higher is more important)
            parent_id: Parent goal ID for sub-goals
            completion_criteria: List of criteria for goal completion
            metadata: Additional metadata
            
        Returns:
            Created goal
        """
        goal = Goal(
            description=description,
            mode=mode,
            priority=priority,
            parent_id=parent_id,
            completion_criteria=completion_criteria or [],
            metadata=metadata or {},
        )
        
        self.goals[goal.id] = goal
        
        # Add to parent's sub-goals if parent exists
        if parent_id and parent_id in self.goals:
            self.goals[parent_id].sub_goals.append(goal.id)
            
        return goal
    
    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get goal by ID."""
        return self.goals.get(goal_id)
    
    def update_goal_status(self, goal_id: str, status: GoalStatus) -> None:
        """Update goal status."""
        if goal_id in self.goals:
            self.goals[goal_id].status = status
            self.goals[goal_id].updated_at = datetime.utcnow()
            
            if status == GoalStatus.COMPLETED:
                self.goals[goal_id].completed_at = datetime.utcnow()
    
    def set_active_goal(self, goal_id: str) -> None:
        """Set the active goal."""
        if goal_id in self.goals:
            self.active_goal_id = goal_id
            self.update_goal_status(goal_id, GoalStatus.IN_PROGRESS)
    
    def get_active_goal(self) -> Optional[Goal]:
        """Get the currently active goal."""
        if self.active_goal_id:
            return self.goals.get(self.active_goal_id)
        return None
    
    def get_next_goal(self) -> Optional[Goal]:
        """
        Get the next goal to work on based on priority.
        
        Returns:
            Next goal to work on, or None
        """
        pending_goals = [
            goal for goal in self.goals.values()
            if goal.status == GoalStatus.PENDING
        ]
        
        if not pending_goals:
            return None
            
        # Sort by priority (highest first)
        pending_goals.sort(key=lambda g: g.priority, reverse=True)
        return pending_goals[0]
    
    def check_goal_completion(self, goal_id: str) -> bool:
        """
        Check if a goal is completed.
        
        Args:
            goal_id: Goal ID
            
        Returns:
            True if goal is completed, False otherwise
        """
        goal = self.get_goal(goal_id)
        if not goal:
            return False
            
        # For continuous goals, never complete
        if goal.mode == GoalMode.CONTINUOUS:
            return False
            
        # Check if all sub-goals are completed
        if goal.sub_goals:
            all_sub_goals_completed = all(
                self.goals[sub_id].status == GoalStatus.COMPLETED
                for sub_id in goal.sub_goals
                if sub_id in self.goals
            )
            return all_sub_goals_completed
            
        # Check completion criteria
        # (In practice, this would be evaluated by the cognitive loop)
        return goal.status == GoalStatus.COMPLETED
    
    def get_goal_hierarchy(self, goal_id: str) -> Dict[str, Any]:
        """
        Get goal hierarchy including parent and children.
        
        Args:
            goal_id: Goal ID
            
        Returns:
            Goal hierarchy
        """
        goal = self.get_goal(goal_id)
        if not goal:
            return {}
            
        hierarchy = {
            "goal": goal.to_dict(),
            "sub_goals": [
                self.get_goal_hierarchy(sub_id)
                for sub_id in goal.sub_goals
                if sub_id in self.goals
            ],
        }
        
        return hierarchy
    
    def list_goals(
        self, status: Optional[GoalStatus] = None, mode: Optional[GoalMode] = None
    ) -> List[Goal]:
        """
        List goals with optional filters.
        
        Args:
            status: Filter by status
            mode: Filter by mode
            
        Returns:
            List of goals
        """
        goals = list(self.goals.values())
        
        if status:
            goals = [g for g in goals if g.status == status]
            
        if mode:
            goals = [g for g in goals if g.mode == mode]
            
        return goals
