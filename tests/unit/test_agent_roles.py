"""Tests for agent roles and coordination."""

import pytest
from xagent.core.agent_roles import AgentRole, AgentInstance, AgentCoordinator


class TestAgentRole:
    """Test AgentRole enum."""
    
    def test_agent_roles_exist(self):
        """Test that all required roles exist."""
        assert AgentRole.WORKER == "worker"
        assert AgentRole.PLANNER == "planner"
        assert AgentRole.CHAT == "chat"
        assert AgentRole.SUB_AGENT == "sub_agent"


class TestAgentInstance:
    """Test AgentInstance dataclass."""
    
    def test_create_agent_instance(self):
        """Test creating an agent instance."""
        agent = AgentInstance(role=AgentRole.WORKER)
        
        assert agent.id is not None
        assert agent.role == AgentRole.WORKER
        assert agent.active is True
        assert agent.current_task is None
        assert agent.parent_agent_id is None
    
    def test_agent_instance_to_dict(self):
        """Test converting agent instance to dict."""
        agent = AgentInstance(
            role=AgentRole.SUB_AGENT,
            current_task="Test task",
            parent_agent_id="parent_123"
        )
        
        data = agent.to_dict()
        
        assert data["role"] == "sub_agent"
        assert data["current_task"] == "Test task"
        assert data["parent_agent_id"] == "parent_123"
        assert data["active"] is True


class TestAgentCoordinator:
    """Test AgentCoordinator."""
    
    def test_initialization(self):
        """Test coordinator initialization."""
        coordinator = AgentCoordinator(max_sub_agents=5)
        
        assert coordinator.max_sub_agents == 5
        assert len(coordinator.get_all_agents()) == 3  # worker + planner + chat
        assert coordinator.get_worker() is not None
        assert coordinator.get_planner() is not None
        assert coordinator.get_chat_agent() is not None
    
    def test_core_agents_initialized(self):
        """Test that core agents are initialized."""
        coordinator = AgentCoordinator()
        
        worker = coordinator.get_worker()
        assert worker.id == "worker"
        assert worker.role == AgentRole.WORKER
        
        planner = coordinator.get_planner()
        assert planner.id == "planner"
        assert planner.role == AgentRole.PLANNER
        
        chat = coordinator.get_chat_agent()
        assert chat.id == "chat"
        assert chat.role == AgentRole.CHAT
    
    def test_spawn_sub_agent(self):
        """Test spawning a sub-agent."""
        coordinator = AgentCoordinator(max_sub_agents=3)
        
        sub = coordinator.spawn_sub_agent(
            task_description="Process data",
            parent_agent_id="worker"
        )
        
        assert sub is not None
        assert sub.role == AgentRole.SUB_AGENT
        assert sub.current_task == "Process data"
        assert sub.parent_agent_id == "worker"
        assert sub.active is True
    
    def test_spawn_sub_agent_limit(self):
        """Test sub-agent spawn limit."""
        coordinator = AgentCoordinator(max_sub_agents=2)
        
        # Spawn first two sub-agents
        sub1 = coordinator.spawn_sub_agent("Task 1", "worker")
        sub2 = coordinator.spawn_sub_agent("Task 2", "worker")
        
        assert sub1 is not None
        assert sub2 is not None
        
        # Try to spawn third - should fail
        sub3 = coordinator.spawn_sub_agent("Task 3", "worker")
        assert sub3 is None
    
    def test_terminate_sub_agent(self):
        """Test terminating a sub-agent."""
        coordinator = AgentCoordinator()
        
        sub = coordinator.spawn_sub_agent("Task", "worker")
        assert sub is not None
        
        agent_id = sub.id
        result = coordinator.terminate_sub_agent(agent_id)
        
        assert result is True
        assert coordinator.get_agent(agent_id) is None
    
    def test_terminate_nonexistent_agent(self):
        """Test terminating non-existent agent."""
        coordinator = AgentCoordinator()
        
        result = coordinator.terminate_sub_agent("nonexistent")
        assert result is False
    
    def test_terminate_core_agent_fails(self):
        """Test that core agents cannot be terminated."""
        coordinator = AgentCoordinator()
        
        result = coordinator.terminate_sub_agent("worker")
        assert result is False
        
        result = coordinator.terminate_sub_agent("planner")
        assert result is False
        
        result = coordinator.terminate_sub_agent("chat")
        assert result is False
    
    def test_get_active_sub_agents(self):
        """Test getting active sub-agents."""
        coordinator = AgentCoordinator(max_sub_agents=3)
        
        coordinator.spawn_sub_agent("Task 1", "worker")
        coordinator.spawn_sub_agent("Task 2", "worker")
        
        sub_agents = coordinator.get_active_sub_agents()
        assert len(sub_agents) == 2
        assert all(agent.role == AgentRole.SUB_AGENT for agent in sub_agents)
    
    def test_update_agent_task(self):
        """Test updating agent task."""
        coordinator = AgentCoordinator()
        
        sub = coordinator.spawn_sub_agent("Original task", "worker")
        assert sub is not None
        
        result = coordinator.update_agent_task(sub.id, "New task")
        assert result is True
        
        updated = coordinator.get_agent(sub.id)
        assert updated is not None
        assert updated.current_task == "New task"
    
    def test_update_nonexistent_agent_task(self):
        """Test updating task for non-existent agent."""
        coordinator = AgentCoordinator()
        
        result = coordinator.update_agent_task("nonexistent", "Task")
        assert result is False
    
    def test_get_status(self):
        """Test getting coordinator status."""
        coordinator = AgentCoordinator(max_sub_agents=3)
        
        coordinator.spawn_sub_agent("Task 1", "worker")
        coordinator.spawn_sub_agent("Task 2", "worker")
        
        status = coordinator.get_status()
        
        assert "worker" in status
        assert "planner" in status
        assert "chat" in status
        assert "sub_agents" in status
        assert status["sub_agents_count"] == 2
        assert status["sub_agents_limit"] == 3
        assert len(status["sub_agents"]) == 2
    
    def test_spawn_and_terminate_cycle(self):
        """Test spawning and terminating sub-agents in cycle."""
        coordinator = AgentCoordinator(max_sub_agents=2)
        
        # Spawn two agents (at limit)
        sub1 = coordinator.spawn_sub_agent("Task 1", "worker")
        sub2 = coordinator.spawn_sub_agent("Task 2", "worker")
        assert sub1 is not None
        assert sub2 is not None
        
        # Cannot spawn third
        sub3 = coordinator.spawn_sub_agent("Task 3", "worker")
        assert sub3 is None
        
        # Terminate one
        coordinator.terminate_sub_agent(sub1.id)
        
        # Now can spawn again
        sub4 = coordinator.spawn_sub_agent("Task 4", "worker")
        assert sub4 is not None
        
        # Verify count
        assert len(coordinator.get_active_sub_agents()) == 2
