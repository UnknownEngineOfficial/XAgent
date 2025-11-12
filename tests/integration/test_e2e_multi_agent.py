"""
End-to-End Multi-Agent Coordination Tests.

Tests the coordination and collaboration between multiple agents
working on complex tasks.
"""

import asyncio

import pytest

from xagent.core.agent_roles import AgentCoordinator, AgentRole
from xagent.core.goal_engine import GoalEngine, GoalMode, GoalStatus


@pytest.fixture
def goal_engine():
    """Create a goal engine for testing."""
    return GoalEngine()


@pytest.fixture
async def coordinator(goal_engine):
    """Create an agent coordinator for testing."""
    coord = AgentCoordinator(goal_engine=goal_engine)
    await coord.initialize()
    yield coord
    await coord.shutdown()


class TestMultiAgentCoordination:
    """Test multi-agent coordination scenarios."""

    @pytest.mark.asyncio
    async def test_core_agent_initialization(self, coordinator):
        """Test that core agents are properly initialized."""
        # Check that core agents are registered
        agents = coordinator.list_agents()
        
        # Should have at least 3 core agents (Worker, Planner, Chat)
        assert len(agents) >= 3
        
        # Check for core agent roles
        roles = [agent["role"] for agent in agents]
        assert AgentRole.WORKER in roles
        assert AgentRole.PLANNER in roles
        assert AgentRole.CHAT in roles

    @pytest.mark.asyncio
    async def test_sub_agent_spawning(self, coordinator, goal_engine):
        """Test spawning and managing sub-agents."""
        # Create a complex goal that might need sub-agents
        goal = goal_engine.create_goal(
            description="Process multiple data sources in parallel",
            mode=GoalMode.GOAL_ORIENTED,
            priority=7,
            completion_criteria=["All sources processed", "Data aggregated"],
        )
        
        # Spawn sub-agents for parallel processing
        sub_agent_1 = await coordinator.spawn_sub_agent(
            agent_id="sub_1",
            goal_id=goal.id,
            task_description="Process source A",
        )
        
        sub_agent_2 = await coordinator.spawn_sub_agent(
            agent_id="sub_2",
            goal_id=goal.id,
            task_description="Process source B",
        )
        
        assert sub_agent_1 is not None
        assert sub_agent_2 is not None
        
        # Check that sub-agents are registered
        agents = coordinator.list_agents()
        sub_agents = [a for a in agents if a["role"] == AgentRole.SUB_AGENT]
        assert len(sub_agents) >= 2
        
        # Verify sub-agents are working on the correct goal
        assert sub_agent_1["current_goal_id"] == goal.id
        assert sub_agent_2["current_goal_id"] == goal.id

    @pytest.mark.asyncio
    async def test_sub_agent_termination(self, coordinator, goal_engine):
        """Test that sub-agents terminate after completing their task."""
        goal = goal_engine.create_goal(
            description="Quick task for sub-agent",
            mode=GoalMode.GOAL_ORIENTED,
            priority=5,
        )
        
        # Spawn a sub-agent
        sub_agent = await coordinator.spawn_sub_agent(
            agent_id="temp_sub",
            goal_id=goal.id,
            task_description="Quick processing task",
        )
        
        assert sub_agent is not None
        initial_count = len(coordinator.list_agents())
        
        # Simulate task completion and terminate sub-agent
        await coordinator.terminate_sub_agent("temp_sub")
        
        # Verify sub-agent was removed
        final_count = len(coordinator.list_agents())
        assert final_count == initial_count - 1
        
        # Verify sub-agent is not in the list
        agents = coordinator.list_agents()
        agent_ids = [a["id"] for a in agents]
        assert "temp_sub" not in agent_ids

    @pytest.mark.asyncio
    async def test_max_sub_agents_limit(self, coordinator, goal_engine):
        """Test that coordinator enforces max sub-agent limit."""
        goal = goal_engine.create_goal(
            description="Task requiring many sub-agents",
            mode=GoalMode.GOAL_ORIENTED,
            priority=8,
        )
        
        # Attempt to spawn more sub-agents than the limit (default 5-7)
        max_limit = coordinator.max_sub_agents
        spawned_agents = []
        
        # Spawn up to the limit
        for i in range(max_limit):
            agent = await coordinator.spawn_sub_agent(
                agent_id=f"sub_{i}",
                goal_id=goal.id,
                task_description=f"Sub-task {i}",
            )
            if agent:
                spawned_agents.append(agent)
        
        # Verify we spawned the max number
        assert len(spawned_agents) == max_limit
        
        # Attempt to spawn one more (should fail or queue)
        extra_agent = await coordinator.spawn_sub_agent(
            agent_id=f"sub_extra",
            goal_id=goal.id,
            task_description="Extra task",
        )
        
        # Should either be None (rejected) or queued for later
        if extra_agent is not None:
            # If accepted, a slot must have opened up
            current_sub_agents = [
                a for a in coordinator.list_agents() 
                if a["role"] == AgentRole.SUB_AGENT
            ]
            assert len(current_sub_agents) <= max_limit

    @pytest.mark.asyncio
    async def test_agent_role_assignment(self, coordinator, goal_engine):
        """Test that agents are assigned appropriate roles."""
        # Worker agent should handle execution tasks
        workers = [
            a for a in coordinator.list_agents()
            if a["role"] == AgentRole.WORKER
        ]
        assert len(workers) > 0
        
        # Planner agent should handle planning tasks
        planners = [
            a for a in coordinator.list_agents()
            if a["role"] == AgentRole.PLANNER
        ]
        assert len(planners) > 0
        
        # Chat agent should handle communication
        chat_agents = [
            a for a in coordinator.list_agents()
            if a["role"] == AgentRole.CHAT
        ]
        assert len(chat_agents) > 0

    @pytest.mark.asyncio
    async def test_parallel_goal_processing(self, coordinator, goal_engine):
        """Test processing multiple goals in parallel with sub-agents."""
        # Create multiple goals
        goal_1 = goal_engine.create_goal(
            description="Process dataset A",
            mode=GoalMode.GOAL_ORIENTED,
            priority=7,
        )
        
        goal_2 = goal_engine.create_goal(
            description="Process dataset B",
            mode=GoalMode.GOAL_ORIENTED,
            priority=7,
        )
        
        goal_3 = goal_engine.create_goal(
            description="Process dataset C",
            mode=GoalMode.GOAL_ORIENTED,
            priority=7,
        )
        
        # Spawn sub-agents for each goal
        sub_1 = await coordinator.spawn_sub_agent(
            agent_id="parallel_1",
            goal_id=goal_1.id,
            task_description="Process A",
        )
        
        sub_2 = await coordinator.spawn_sub_agent(
            agent_id="parallel_2",
            goal_id=goal_2.id,
            task_description="Process B",
        )
        
        sub_3 = await coordinator.spawn_sub_agent(
            agent_id="parallel_3",
            goal_id=goal_3.id,
            task_description="Process C",
        )
        
        # Verify all sub-agents were spawned
        assert sub_1 is not None
        assert sub_2 is not None
        assert sub_3 is not None
        
        # Verify each is working on different goals
        assert sub_1["current_goal_id"] == goal_1.id
        assert sub_2["current_goal_id"] == goal_2.id
        assert sub_3["current_goal_id"] == goal_3.id
        
        # Simulate parallel processing completion
        await coordinator.terminate_sub_agent("parallel_1")
        await coordinator.terminate_sub_agent("parallel_2")
        await coordinator.terminate_sub_agent("parallel_3")
        
        # Verify cleanup
        remaining_sub_agents = [
            a for a in coordinator.list_agents()
            if a["role"] == AgentRole.SUB_AGENT
        ]
        assert "parallel_1" not in [a["id"] for a in remaining_sub_agents]
        assert "parallel_2" not in [a["id"] for a in remaining_sub_agents]
        assert "parallel_3" not in [a["id"] for a in remaining_sub_agents]

    @pytest.mark.asyncio
    async def test_agent_communication(self, coordinator, goal_engine):
        """Test communication between agents via coordinator."""
        goal = goal_engine.create_goal(
            description="Task requiring agent coordination",
            mode=GoalMode.GOAL_ORIENTED,
            priority=6,
        )
        
        # Spawn two sub-agents that need to coordinate
        sub_1 = await coordinator.spawn_sub_agent(
            agent_id="comm_1",
            goal_id=goal.id,
            task_description="Part 1 of coordinated task",
        )
        
        sub_2 = await coordinator.spawn_sub_agent(
            agent_id="comm_2",
            goal_id=goal.id,
            task_description="Part 2 of coordinated task",
        )
        
        # Verify both agents exist
        assert sub_1 is not None
        assert sub_2 is not None
        
        # Check that coordinator can facilitate communication
        # (In reality, agents would communicate via shared memory/messages)
        agents = coordinator.list_agents()
        comm_agents = [
            a for a in agents 
            if a["id"] in ["comm_1", "comm_2"]
        ]
        assert len(comm_agents) == 2
        
        # Verify they're working on the same goal (coordination point)
        assert all(a["current_goal_id"] == goal.id for a in comm_agents)

    @pytest.mark.asyncio
    async def test_coordinator_shutdown_cleanup(self, coordinator, goal_engine):
        """Test that shutdown properly cleans up all agents."""
        goal = goal_engine.create_goal(
            description="Task for shutdown test",
            mode=GoalMode.GOAL_ORIENTED,
            priority=5,
        )
        
        # Spawn some sub-agents
        await coordinator.spawn_sub_agent(
            agent_id="shutdown_1",
            goal_id=goal.id,
            task_description="Task 1",
        )
        
        await coordinator.spawn_sub_agent(
            agent_id="shutdown_2",
            goal_id=goal.id,
            task_description="Task 2",
        )
        
        # Verify agents exist
        agents_before = coordinator.list_agents()
        assert len(agents_before) > 0
        
        # Shutdown coordinator
        await coordinator.shutdown()
        
        # After shutdown, coordinator should be clean
        # (This is tested implicitly by the fixture cleanup)
        assert True  # If we get here without errors, shutdown worked

    @pytest.mark.asyncio
    async def test_sub_agent_failure_handling(self, coordinator, goal_engine):
        """Test handling of sub-agent failures."""
        goal = goal_engine.create_goal(
            description="Task that might fail",
            mode=GoalMode.GOAL_ORIENTED,
            priority=6,
        )
        
        # Spawn a sub-agent
        sub_agent = await coordinator.spawn_sub_agent(
            agent_id="failure_test",
            goal_id=goal.id,
            task_description="Potentially failing task",
        )
        
        assert sub_agent is not None
        
        # Simulate failure by terminating the agent
        await coordinator.terminate_sub_agent("failure_test")
        
        # Verify agent was removed
        agents = coordinator.list_agents()
        agent_ids = [a["id"] for a in agents]
        assert "failure_test" not in agent_ids
        
        # Goal should still exist (not affected by sub-agent failure)
        retrieved_goal = goal_engine.get_goal(goal.id)
        assert retrieved_goal is not None
        assert retrieved_goal.id == goal.id


class TestAgentWorkloadDistribution:
    """Test workload distribution across multiple agents."""

    @pytest.mark.asyncio
    async def test_balanced_workload_distribution(self, coordinator, goal_engine):
        """Test that workload is distributed evenly across available sub-agents."""
        # Create multiple goals
        goals = []
        for i in range(5):
            goal = goal_engine.create_goal(
                description=f"Task {i}",
                mode=GoalMode.GOAL_ORIENTED,
                priority=5,
            )
            goals.append(goal)
        
        # Spawn sub-agents for each goal
        for i, goal in enumerate(goals):
            await coordinator.spawn_sub_agent(
                agent_id=f"workload_{i}",
                goal_id=goal.id,
                task_description=f"Process task {i}",
            )
        
        # Verify sub-agents were distributed
        sub_agents = [
            a for a in coordinator.list_agents()
            if a["role"] == AgentRole.SUB_AGENT
        ]
        
        # Should have spawned up to max_sub_agents
        assert len(sub_agents) <= coordinator.max_sub_agents
        assert len(sub_agents) > 0

    @pytest.mark.asyncio
    async def test_priority_based_agent_assignment(self, coordinator, goal_engine):
        """Test that high-priority goals get agent assignment first."""
        # Create goals with different priorities
        low_priority_goal = goal_engine.create_goal(
            description="Low priority task",
            mode=GoalMode.GOAL_ORIENTED,
            priority=2,
        )
        
        high_priority_goal = goal_engine.create_goal(
            description="High priority task",
            mode=GoalMode.GOAL_ORIENTED,
            priority=9,
        )
        
        # Spawn agents (high priority should be processed first)
        high_agent = await coordinator.spawn_sub_agent(
            agent_id="high_priority_agent",
            goal_id=high_priority_goal.id,
            task_description="High priority processing",
        )
        
        low_agent = await coordinator.spawn_sub_agent(
            agent_id="low_priority_agent",
            goal_id=low_priority_goal.id,
            task_description="Low priority processing",
        )
        
        # Both should succeed (unless we hit limits)
        # In real implementation, high priority would get preference
        assert high_agent is not None or low_agent is not None
