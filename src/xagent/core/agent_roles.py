"""Agent Roles - Limited multi-agent coordination for XAgent."""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
import uuid


class AgentRole(str, Enum):
    """Agent roles for internal coordination.
    
    XAgent uses a limited number of internal agents for specific purposes:
    - WORKER: Primary execution agent for tasks and actions
    - PLANNER: Strategic planning and goal decomposition
    - CHAT: User communication and interaction
    - SUB_AGENT: Temporary worker for subtasks (spawned as needed, max 5-7)
    """
    
    WORKER = "worker"
    PLANNER = "planner"
    CHAT = "chat"
    SUB_AGENT = "sub_agent"


@dataclass
class AgentInstance:
    """Represents an agent instance within XAgent."""
    
    id: str = field(default_factory=lambda: f"agent_{str(uuid.uuid4())[:8]}")
    role: AgentRole = AgentRole.WORKER
    active: bool = True
    current_task: Optional[str] = None
    parent_agent_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "role": self.role.value,
            "active": self.active,
            "current_task": self.current_task,
            "parent_agent_id": self.parent_agent_id,
            "metadata": self.metadata,
        }


class AgentCoordinator:
    """Coordinates limited internal agents in XAgent.
    
    Manages:
    - 1 Worker Agent (primary execution and action)
    - 1 Planner Agent (strategic planning and goal decomposition)
    - 1 Chat Agent (user communication and interaction)
    - N Sub-Agents (temporary subtask workers, max 5-7, configurable)
    """
    
    def __init__(self, max_sub_agents: int = 5):
        """Initialize agent coordinator.
        
        Args:
            max_sub_agents: Maximum number of concurrent sub-agents (default: 5, max recommended: 7)
        """
        self.max_sub_agents = max_sub_agents
        self.agents: dict[str, AgentInstance] = {}
        
        # Initialize core agents
        self._initialize_core_agents()
    
    def _initialize_core_agents(self) -> None:
        """Initialize the core agents (worker, planner, and chat)."""
        # Worker agent - primary execution
        worker = AgentInstance(
            id="worker",
            role=AgentRole.WORKER,
        )
        self.agents[worker.id] = worker
        
        # Planner agent - strategic planning
        planner = AgentInstance(
            id="planner",
            role=AgentRole.PLANNER,
        )
        self.agents[planner.id] = planner
        
        # Chat agent - user communication
        chat_agent = AgentInstance(
            id="chat",
            role=AgentRole.CHAT,
        )
        self.agents[chat_agent.id] = chat_agent
    
    def spawn_sub_agent(self, task_description: str, parent_agent_id: str) -> Optional[AgentInstance]:
        """Spawn a temporary sub-agent for subtask execution.
        
        Args:
            task_description: Description of the subtask
            parent_agent_id: ID of the parent agent spawning this sub-agent
            
        Returns:
            AgentInstance if successfully spawned, None if limit reached
        """
        # Check if we've reached the limit
        active_sub_agents = self.get_active_sub_agents()
        if len(active_sub_agents) >= self.max_sub_agents:
            return None
        
        # Create sub-agent
        sub_agent = AgentInstance(
            role=AgentRole.SUB_AGENT,
            current_task=task_description,
            parent_agent_id=parent_agent_id,
        )
        
        self.agents[sub_agent.id] = sub_agent
        return sub_agent
    
    def terminate_sub_agent(self, agent_id: str) -> bool:
        """Terminate a sub-agent after subtask completion.
        
        Args:
            agent_id: ID of the sub-agent to terminate
            
        Returns:
            True if successfully terminated, False otherwise
        """
        if agent_id not in self.agents:
            return False
        
        agent = self.agents[agent_id]
        if agent.role != AgentRole.SUB_AGENT:
            return False
        
        agent.active = False
        del self.agents[agent_id]
        return True
    
    def get_agent(self, agent_id: str) -> Optional[AgentInstance]:
        """Get agent by ID."""
        return self.agents.get(agent_id)
    
    def get_worker(self) -> AgentInstance:
        """Get the worker agent."""
        return self.agents["worker"]
    
    def get_planner(self) -> AgentInstance:
        """Get the planner agent."""
        return self.agents["planner"]
    
    def get_chat_agent(self) -> AgentInstance:
        """Get the chat agent."""
        return self.agents["chat"]
    
    def get_active_sub_agents(self) -> list[AgentInstance]:
        """Get all active sub-agents."""
        return [
            agent for agent in self.agents.values()
            if agent.role == AgentRole.SUB_AGENT and agent.active
        ]
    
    def get_all_agents(self) -> list[AgentInstance]:
        """Get all agents."""
        return list(self.agents.values())
    
    def update_agent_task(self, agent_id: str, task_description: str) -> bool:
        """Update the current task for an agent.
        
        Args:
            agent_id: ID of the agent
            task_description: New task description
            
        Returns:
            True if successfully updated, False otherwise
        """
        if agent_id not in self.agents:
            return False
        
        self.agents[agent_id].current_task = task_description
        return True
    
    def get_status(self) -> dict:
        """Get status of all agents."""
        return {
            "worker": self.get_worker().to_dict(),
            "planner": self.get_planner().to_dict(),
            "chat": self.get_chat_agent().to_dict(),
            "sub_agents": [agent.to_dict() for agent in self.get_active_sub_agents()],
            "sub_agents_count": len(self.get_active_sub_agents()),
            "sub_agents_limit": self.max_sub_agents,
        }
