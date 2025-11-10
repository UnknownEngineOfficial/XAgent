"""Tests for agent roles and coordination."""

import pytest
from xagent.core.agent_roles import AgentRole, AgentInstance, AgentCoordinator


class TestAgentRole:
    """Test AgentRole enum."""
    
    def test_agent_roles_exist(self):
        """Test that all required roles exist."""
        assert AgentRole.MAIN_WORKER == "main_worker"
        assert AgentRole.USER_INTERFACE == "user_interface"
        assert AgentRole.MINI_AGENT == "mini_agent"


class TestAgentInstance:
    """Test AgentInstance dataclass."""
    
    def test_create_agent_instance(self):
        """Test creating an agent instance."""
        agent = AgentInstance(role=AgentRole.MAIN_WORKER)
        
        assert agent.id is not None
        assert agent.role == AgentRole.MAIN_WORKER
        assert agent.active is True
        assert agent.current_task is None
        assert agent.parent_agent_id is None
    
    def test_agent_instance_to_dict(self):
        """Test converting agent instance to dict."""
        agent = AgentInstance(
            role=AgentRole.MINI_AGENT,
            current_task="Test task",
            parent_agent_id="parent_123"
        )
        
        data = agent.to_dict()
        
        assert data["role"] == "mini_agent"
        assert data["current_task"] == "Test task"
        assert data["parent_agent_id"] == "parent_123"
        assert data["active"] is True


class TestAgentCoordinator:
    """Test AgentCoordinator."""
    
    def test_initialization(self):
        """Test coordinator initialization."""
        coordinator = AgentCoordinator(max_mini_agents=5)
        
        assert coordinator.max_mini_agents == 5
        assert len(coordinator.get_all_agents()) == 2  # worker + UI
        assert coordinator.get_main_worker() is not None
        assert coordinator.get_user_interface_agent() is not None
    
    def test_core_agents_initialized(self):
        """Test that core agents are initialized."""
        coordinator = AgentCoordinator()
        
        worker = coordinator.get_main_worker()
        assert worker.id == "main_worker"
        assert worker.role == AgentRole.MAIN_WORKER
        
        ui = coordinator.get_user_interface_agent()
        assert ui.id == "user_interface"
        assert ui.role == AgentRole.USER_INTERFACE
    
    def test_spawn_mini_agent(self):
        """Test spawning a mini-agent."""
        coordinator = AgentCoordinator(max_mini_agents=3)
        
        mini = coordinator.spawn_mini_agent(
            task_description="Process data",
            parent_agent_id="main_worker"
        )
        
        assert mini is not None
        assert mini.role == AgentRole.MINI_AGENT
        assert mini.current_task == "Process data"
        assert mini.parent_agent_id == "main_worker"
        assert mini.active is True
    
    def test_spawn_mini_agent_limit(self):
        """Test mini-agent spawn limit."""
        coordinator = AgentCoordinator(max_mini_agents=2)
        
        # Spawn first two mini-agents
        mini1 = coordinator.spawn_mini_agent("Task 1", "main_worker")
        mini2 = coordinator.spawn_mini_agent("Task 2", "main_worker")
        
        assert mini1 is not None
        assert mini2 is not None
        
        # Try to spawn third - should fail
        mini3 = coordinator.spawn_mini_agent("Task 3", "main_worker")
        assert mini3 is None
    
    def test_terminate_mini_agent(self):
        """Test terminating a mini-agent."""
        coordinator = AgentCoordinator()
        
        mini = coordinator.spawn_mini_agent("Task", "main_worker")
        assert mini is not None
        
        agent_id = mini.id
        result = coordinator.terminate_mini_agent(agent_id)
        
        assert result is True
        assert coordinator.get_agent(agent_id) is None
    
    def test_terminate_nonexistent_agent(self):
        """Test terminating non-existent agent."""
        coordinator = AgentCoordinator()
        
        result = coordinator.terminate_mini_agent("nonexistent")
        assert result is False
    
    def test_terminate_core_agent_fails(self):
        """Test that core agents cannot be terminated."""
        coordinator = AgentCoordinator()
        
        result = coordinator.terminate_mini_agent("main_worker")
        assert result is False
        
        result = coordinator.terminate_mini_agent("user_interface")
        assert result is False
    
    def test_get_active_mini_agents(self):
        """Test getting active mini-agents."""
        coordinator = AgentCoordinator(max_mini_agents=3)
        
        coordinator.spawn_mini_agent("Task 1", "main_worker")
        coordinator.spawn_mini_agent("Task 2", "main_worker")
        
        mini_agents = coordinator.get_active_mini_agents()
        assert len(mini_agents) == 2
        assert all(agent.role == AgentRole.MINI_AGENT for agent in mini_agents)
    
    def test_update_agent_task(self):
        """Test updating agent task."""
        coordinator = AgentCoordinator()
        
        mini = coordinator.spawn_mini_agent("Original task", "main_worker")
        assert mini is not None
        
        result = coordinator.update_agent_task(mini.id, "New task")
        assert result is True
        
        updated = coordinator.get_agent(mini.id)
        assert updated is not None
        assert updated.current_task == "New task"
    
    def test_update_nonexistent_agent_task(self):
        """Test updating task for non-existent agent."""
        coordinator = AgentCoordinator()
        
        result = coordinator.update_agent_task("nonexistent", "Task")
        assert result is False
    
    def test_get_status(self):
        """Test getting coordinator status."""
        coordinator = AgentCoordinator(max_mini_agents=3)
        
        coordinator.spawn_mini_agent("Task 1", "main_worker")
        coordinator.spawn_mini_agent("Task 2", "main_worker")
        
        status = coordinator.get_status()
        
        assert "main_worker" in status
        assert "user_interface" in status
        assert "mini_agents" in status
        assert status["mini_agents_count"] == 2
        assert status["mini_agents_limit"] == 3
        assert len(status["mini_agents"]) == 2
    
    def test_spawn_and_terminate_cycle(self):
        """Test spawning and terminating mini-agents in cycle."""
        coordinator = AgentCoordinator(max_mini_agents=2)
        
        # Spawn two agents (at limit)
        mini1 = coordinator.spawn_mini_agent("Task 1", "main_worker")
        mini2 = coordinator.spawn_mini_agent("Task 2", "main_worker")
        assert mini1 is not None
        assert mini2 is not None
        
        # Cannot spawn third
        mini3 = coordinator.spawn_mini_agent("Task 3", "main_worker")
        assert mini3 is None
        
        # Terminate one
        coordinator.terminate_mini_agent(mini1.id)
        
        # Now can spawn again
        mini4 = coordinator.spawn_mini_agent("Task 4", "main_worker")
        assert mini4 is not None
        
        # Verify count
        assert len(coordinator.get_active_mini_agents()) == 2
