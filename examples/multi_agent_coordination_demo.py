"""
Multi-Agent Coordination Demo - XAgent Limited Internal Agents.

This demo shows how XAgent uses a limited number of internal agents for:
1. Main Worker Agent - Primary task execution
2. User Interface Agent - User communication handling
3. Mini-Agents - Temporary workers for parallel subtasks (limited to 3-5)

Note: This is NOT a full multi-agent system. For that, use XTeam.
XAgent uses limited internal coordination for efficiency while remaining
integrable into larger multi-agent systems.
"""

import asyncio
from xagent.core.agent import XAgent
from xagent.config import Settings


async def demo_basic_agent_coordination():
    """Demonstrate basic agent coordination."""
    print("=" * 60)
    print("XAgent Multi-Agent Coordination Demo")
    print("=" * 60)
    print()
    
    # Create settings with custom max mini-agents
    settings = Settings(max_mini_agents=3)
    
    # Initialize agent
    agent = XAgent(settings=settings)
    await agent.initialize()
    
    print("✓ XAgent initialized with internal agent coordination")
    print(f"  - Max mini-agents: {settings.max_mini_agents}")
    print()
    
    # Show initial agent status
    status = await agent.get_status()
    print("Initial Agent Status:")
    print(f"  Main Worker: {status['agents']['main_worker']['id']}")
    print(f"  User Interface: {status['agents']['user_interface']['id']}")
    print(f"  Mini-Agents Active: {status['agents']['mini_agents_count']}/{status['agents']['mini_agents_limit']}")
    print()
    
    # Start agent with main goal
    print("Starting agent with main goal...")
    await agent.start("Process complex data analysis task")
    await asyncio.sleep(0.5)
    print()
    
    # Spawn mini-agents for subtasks
    print("Spawning mini-agents for parallel subtasks...")
    
    subtasks = [
        "Load and preprocess data",
        "Analyze data patterns",
        "Generate visualizations"
    ]
    
    spawned_agents = []
    for i, subtask in enumerate(subtasks, 1):
        print(f"  {i}. Spawning mini-agent for: {subtask}")
        agent_id = await agent.spawn_subtask_agent(
            task_description=subtask,
            parent_goal_id=None
        )
        if agent_id:
            spawned_agents.append(agent_id)
            print(f"     ✓ Spawned mini-agent: {agent_id}")
        else:
            print(f"     ✗ Failed to spawn mini-agent (limit reached)")
        await asyncio.sleep(0.2)
    
    print()
    
    # Show updated status with mini-agents
    status = await agent.get_status()
    print("Agent Status After Spawning:")
    print(f"  Mini-Agents Active: {status['agents']['mini_agents_count']}/{status['agents']['mini_agents_limit']}")
    print("  Active Mini-Agents:")
    for mini in status['agents']['mini_agents']:
        print(f"    - {mini['id']}: {mini['current_task']}")
    print()
    
    # Try spawning beyond limit
    print("Attempting to spawn beyond limit...")
    extra_agent = await agent.spawn_subtask_agent(
        task_description="Extra task beyond limit",
        parent_goal_id=None
    )
    if extra_agent:
        print(f"  ✓ Spawned extra agent: {extra_agent}")
    else:
        print(f"  ✗ Cannot spawn (limit of {settings.max_mini_agents} reached)")
    print()
    
    # Simulate work and terminate mini-agents
    print("Simulating subtask completion...")
    await asyncio.sleep(1)
    
    for agent_id in spawned_agents[:1]:  # Terminate first agent
        print(f"  Terminating mini-agent: {agent_id}")
        result = await agent.terminate_subtask_agent(agent_id)
        print(f"    {'✓' if result else '✗'} Termination {'successful' if result else 'failed'}")
    
    print()
    
    # Show final status
    status = await agent.get_status()
    print("Final Agent Status:")
    print(f"  Mini-Agents Active: {status['agents']['mini_agents_count']}/{status['agents']['mini_agents_limit']}")
    print(f"  Goals Total: {status['goals_summary']['total']}")
    print(f"  Goals In Progress: {status['goals_summary']['in_progress']}")
    print()
    
    # Cleanup
    await agent.stop()
    print("✓ Agent stopped successfully")


async def demo_user_interaction_while_working():
    """Demonstrate user interaction while worker agent is busy."""
    print()
    print("=" * 60)
    print("User Interaction During Work Demo")
    print("=" * 60)
    print()
    
    agent = XAgent()
    await agent.initialize()
    await agent.start("Perform long-running computation")
    
    print("Main worker is busy with long-running task...")
    print("User interface agent handles user communication separately")
    print()
    
    # Simulate user commands while work is ongoing
    user_commands = [
        "What's the current progress?",
        "Can you add another subtask?",
        "Show me the status"
    ]
    
    for cmd in user_commands:
        print(f"User: {cmd}")
        await agent.send_command(cmd)
        await asyncio.sleep(0.3)
        print(f"  → Routed to User Interface Agent")
        print()
    
    await agent.stop()
    print("✓ Demo completed")


async def demo_concept_explanation():
    """Explain the XAgent multi-agent concept."""
    print()
    print("=" * 60)
    print("XAgent Multi-Agent Concept Explanation")
    print("=" * 60)
    print()
    
    explanation = """
XAgent's Limited Multi-Agent Coordination:

1. PHILOSOPHY:
   - XAgent is NOT a full multi-agent system
   - XAgent uses limited internal agents for specific purposes
   - Full multi-agent systems are handled by XTeam

2. INTERNAL AGENTS:
   ┌─────────────────────────────────────┐
   │ Main Worker Agent                   │
   │ - Primary task execution            │
   │ - Goal processing                   │
   │ - Tool usage                        │
   └─────────────────────────────────────┘
   
   ┌─────────────────────────────────────┐
   │ User Interface Agent                │
   │ - User communication                │
   │ - Command routing                   │
   │ - Status reporting                  │
   └─────────────────────────────────────┘
   
   ┌─────────────────────────────────────┐
   │ Mini-Agents (3-5 max)               │
   │ - Temporary subtask workers         │
   │ - Parallel execution                │
   │ - Auto-terminated after completion  │
   └─────────────────────────────────────┘

3. WHY THIS DESIGN?
   ✓ Clear separation of concerns
   ✓ Multi-tasking without overhead
   ✓ User interaction while working
   ✓ Parallel subtask execution
   ✓ Remains integrable into XTeam
   ✓ Avoids architecture bloat

4. FOR FULL MULTI-AGENT SYSTEMS:
   Use XTeam to orchestrate multiple XAgent instances:
   - XTeam manages agent-to-agent communication
   - XTeam handles collective intelligence
   - XTeam distributes tasks across agents
   - Each XAgent remains focused and lightweight

5. LIMITS:
   - Max 3-5 mini-agents (configurable)
   - Mini-agents are temporary
   - Core agents (worker + UI) always present
   - Designed for efficiency, not swarm intelligence
"""
    
    print(explanation)


async def main():
    """Run all demos."""
    try:
        # Demo 1: Basic coordination
        await demo_basic_agent_coordination()
        
        # Demo 2: User interaction
        await demo_user_interaction_while_working()
        
        # Demo 3: Concept explanation
        await demo_concept_explanation()
        
        print()
        print("=" * 60)
        print("All Demos Completed Successfully!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\nError during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
