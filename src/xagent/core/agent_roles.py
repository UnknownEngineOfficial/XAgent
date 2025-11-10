"""Agent Roles - Limited multi-agent coordination for XAgent."""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
import uuid


class AgentRole(str, Enum):
    """Agent roles for internal coordination.
    
    XAgent uses a limited number of internal agents for specific purposes:
    - MAIN_WORKER: Primary execution agent for tasks
    - USER_INTERFACE: Dedicated agent for user communication
    - MINI_AGENT: Temporary worker for subtasks (spawned as needed)
    """
    
    MAIN_WORKER = "main_worker"
    USER_INTERFACE = "user_interface"
    MINI_AGENT = "mini_agent"


@dataclass
class AgentInstance:
    """Represents an agent instance within XAgent."""
    
    id: str = field(default_factory=lambda: f"agent_{str(uuid.uuid4())[:8]}")
    role: AgentRole = AgentRole.MAIN_WORKER
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
    - 1 Main Worker Agent (primary execution)
    - 1 User Interface Agent (user communication)
    - N Mini-Agents (temporary subtask workers, limited by config)
    """
    
    def __init__(self, max_mini_agents: int = 3):
        """Initialize agent coordinator.
        
        Args:
            max_mini_agents: Maximum number of concurrent mini-agents (default: 3)
        """
        self.max_mini_agents = max_mini_agents
        self.agents: dict[str, AgentInstance] = {}
        
        # Initialize core agents
        self._initialize_core_agents()
    
    def _initialize_core_agents(self) -> None:
        """Initialize the core agents (worker and user interface)."""
        # Main worker agent
        worker = AgentInstance(
            id="main_worker",
            role=AgentRole.MAIN_WORKER,
        )
        self.agents[worker.id] = worker
        
        # User interface agent
        ui_agent = AgentInstance(
            id="user_interface",
            role=AgentRole.USER_INTERFACE,
        )
        self.agents[ui_agent.id] = ui_agent
    
    def spawn_mini_agent(self, task_description: str, parent_agent_id: str) -> Optional[AgentInstance]:
        """Spawn a temporary mini-agent for subtask execution.
        
        Args:
            task_description: Description of the subtask
            parent_agent_id: ID of the parent agent spawning this mini-agent
            
        Returns:
            AgentInstance if successfully spawned, None if limit reached
        """
        # Check if we've reached the limit
        active_mini_agents = self.get_active_mini_agents()
        if len(active_mini_agents) >= self.max_mini_agents:
            return None
        
        # Create mini-agent
        mini_agent = AgentInstance(
            role=AgentRole.MINI_AGENT,
            current_task=task_description,
            parent_agent_id=parent_agent_id,
        )
        
        self.agents[mini_agent.id] = mini_agent
        return mini_agent
    
    def terminate_mini_agent(self, agent_id: str) -> bool:
        """Terminate a mini-agent after subtask completion.
        
        Args:
            agent_id: ID of the mini-agent to terminate
            
        Returns:
            True if successfully terminated, False otherwise
        """
        if agent_id not in self.agents:
            return False
        
        agent = self.agents[agent_id]
        if agent.role != AgentRole.MINI_AGENT:
            return False
        
        agent.active = False
        del self.agents[agent_id]
        return True
    
    def get_agent(self, agent_id: str) -> Optional[AgentInstance]:
        """Get agent by ID."""
        return self.agents.get(agent_id)
    
    def get_main_worker(self) -> AgentInstance:
        """Get the main worker agent."""
        return self.agents["main_worker"]
    
    def get_user_interface_agent(self) -> AgentInstance:
        """Get the user interface agent."""
        return self.agents["user_interface"]
    
    def get_active_mini_agents(self) -> list[AgentInstance]:
        """Get all active mini-agents."""
        return [
            agent for agent in self.agents.values()
            if agent.role == AgentRole.MINI_AGENT and agent.active
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
            "main_worker": self.get_main_worker().to_dict(),
            "user_interface": self.get_user_interface_agent().to_dict(),
            "mini_agents": [agent.to_dict() for agent in self.get_active_mini_agents()],
            "mini_agents_count": len(self.get_active_mini_agents()),
            "mini_agents_limit": self.max_mini_agents,
        }
