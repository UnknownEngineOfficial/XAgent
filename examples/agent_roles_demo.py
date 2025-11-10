"""
Agent Roles Demonstration - No external dependencies.

Shows XAgent's limited multi-agent coordination concept:
- Main Worker Agent
- User Interface Agent  
- Mini-Agents (temporary subtask workers)
"""

from xagent.core.agent_roles import AgentRole, AgentInstance, AgentCoordinator


def demo_agent_roles():
    """Demonstrate agent roles and their purposes."""
    print("=" * 70)
    print("XAgent Agent Roles")
    print("=" * 70)
    print()
    
    print("Available Agent Roles:")
    print(f"  1. {AgentRole.MAIN_WORKER.value:20} - Primary task execution")
    print(f"  2. {AgentRole.USER_INTERFACE.value:20} - User communication")
    print(f"  3. {AgentRole.MINI_AGENT.value:20} - Temporary subtask workers")
    print()


def demo_agent_coordinator():
    """Demonstrate agent coordinator functionality."""
    print("=" * 70)
    print("Agent Coordinator Demo")
    print("=" * 70)
    print()
    
    # Initialize coordinator
    print("Initializing Agent Coordinator (max 3 mini-agents)...")
    coordinator = AgentCoordinator(max_mini_agents=3)
    print("✓ Coordinator initialized")
    print()
    
    # Show core agents
    print("Core Agents (always present):")
    worker = coordinator.get_main_worker()
    ui = coordinator.get_user_interface_agent()
    print(f"  1. Main Worker:      {worker.id}")
    print(f"     Role:             {worker.role.value}")
    print(f"     Active:           {worker.active}")
    print()
    print(f"  2. User Interface:   {ui.id}")
    print(f"     Role:             {ui.role.value}")
    print(f"     Active:           {ui.active}")
    print()
    
    # Spawn mini-agents
    print("Spawning Mini-Agents for Parallel Subtasks:")
    print()
    
    subtasks = [
        "Analyze data patterns",
        "Generate visualizations",
        "Create summary report"
    ]
    
    spawned = []
    for i, task in enumerate(subtasks, 1):
        print(f"  Task {i}: {task}")
        mini = coordinator.spawn_mini_agent(
            task_description=task,
            parent_agent_id=worker.id
        )
        
        if mini:
            spawned.append(mini)
            print(f"    ✓ Spawned mini-agent: {mini.id}")
            print(f"      Current task: {mini.current_task}")
            print(f"      Parent: {mini.parent_agent_id}")
        else:
            print(f"    ✗ Failed to spawn (limit reached)")
        print()
    
    # Show status
    status = coordinator.get_status()
    print("Current Status:")
    print(f"  Active Mini-Agents: {status['mini_agents_count']}/{status['mini_agents_limit']}")
    print()
    
    # Try to exceed limit
    print("Attempting to spawn beyond limit...")
    extra = coordinator.spawn_mini_agent(
        task_description="Extra task",
        parent_agent_id=worker.id
    )
    
    if extra:
        print(f"  ✓ Spawned: {extra.id}")
    else:
        print(f"  ✗ Cannot spawn - limit of {coordinator.max_mini_agents} reached")
    print()
    
    # Terminate a mini-agent
    if spawned:
        agent_to_terminate = spawned[0]
        print(f"Terminating mini-agent: {agent_to_terminate.id}")
        result = coordinator.terminate_mini_agent(agent_to_terminate.id)
        print(f"  {'✓' if result else '✗'} Termination {'successful' if result else 'failed'}")
        print()
        
        # Now can spawn again
        print("Spawning new mini-agent after termination...")
        new_mini = coordinator.spawn_mini_agent(
            task_description="New task after slot freed",
            parent_agent_id=worker.id
        )
        if new_mini:
            print(f"  ✓ Spawned: {new_mini.id}")
        print()
    
    # Final status
    final_status = coordinator.get_status()
    print("Final Status:")
    print(f"  Total Agents: {len(coordinator.get_all_agents())}")
    print(f"  Core Agents: 2 (worker + UI)")
    print(f"  Active Mini-Agents: {final_status['mini_agents_count']}/{final_status['mini_agents_limit']}")
    print()


def demo_concept_explanation():
    """Explain the multi-agent concept."""
    print("=" * 70)
    print("XAgent Multi-Agent Concept")
    print("=" * 70)
    print()
    
    explanation = """
WHY LIMITED MULTI-AGENT COORDINATION?

1. XAgent's Purpose:
   ✓ Single autonomous agent
   ✓ Integrable into multi-agent systems (XTeam)
   ✗ NOT a full multi-agent system itself

2. Internal Agent Architecture:
   
   ┌─────────────────────────────────────┐
   │ Main Worker Agent                   │  Always Present
   │ • Handles primary task execution    │
   │ • Processes goals                   │
   │ • Uses tools and resources          │
   └─────────────────────────────────────┘
   
   ┌─────────────────────────────────────┐
   │ User Interface Agent                │  Always Present
   │ • Manages user communication        │
   │ • Routes commands                   │
   │ • Provides status updates           │
   └─────────────────────────────────────┘
   
   ┌─────────────────────────────────────┐
   │ Mini-Agents (3-5 max)               │  Temporary
   │ • Execute parallel subtasks         │
   │ • Spawned on demand                 │
   │ • Auto-terminated when done         │
   └─────────────────────────────────────┘

3. Benefits:
   ✓ Clear separation: work vs. communication
   ✓ Multi-tasking: work + user interaction simultaneously
   ✓ Parallel execution: subtasks in parallel
   ✓ No overhead: limited number of agents
   ✓ Integrable: works as component in larger systems

4. For Full Multi-Agent Systems:
   → Use XTeam to orchestrate multiple XAgent instances
   → Each XAgent remains focused and lightweight
   → XTeam handles inter-agent coordination
   → Collective intelligence at XTeam level

5. Configuration:
   • max_mini_agents: 3-5 (default: 3)
   • Adjustable via Settings
   • Prevents architecture bloat
"""
    
    print(explanation)


def demo_use_cases():
    """Show practical use cases."""
    print("=" * 70)
    print("Practical Use Cases")
    print("=" * 70)
    print()
    
    use_cases = [
        {
            "scenario": "Data Processing Pipeline",
            "main_worker": "Coordinate overall pipeline",
            "user_interface": "Report progress to user",
            "mini_agents": [
                "Load and validate data",
                "Transform data",
                "Save results"
            ]
        },
        {
            "scenario": "Research Task",
            "main_worker": "Plan research strategy",
            "user_interface": "Answer user questions",
            "mini_agents": [
                "Search academic papers",
                "Extract key insights",
                "Generate bibliography"
            ]
        },
        {
            "scenario": "Code Review",
            "main_worker": "Analyze codebase structure",
            "user_interface": "Provide feedback",
            "mini_agents": [
                "Check style violations",
                "Analyze security issues",
                "Suggest improvements"
            ]
        }
    ]
    
    for i, uc in enumerate(use_cases, 1):
        print(f"{i}. {uc['scenario']}")
        print(f"   Main Worker:     {uc['main_worker']}")
        print(f"   User Interface:  {uc['user_interface']}")
        print(f"   Mini-Agents:")
        for j, mini_task in enumerate(uc['mini_agents'], 1):
            print(f"     {j}) {mini_task}")
        print()


def main():
    """Run all demonstrations."""
    try:
        demo_agent_roles()
        demo_agent_coordinator()
        demo_concept_explanation()
        demo_use_cases()
        
        print("=" * 70)
        print("Demo Completed Successfully!")
        print("=" * 70)
        print()
        print("Key Takeaways:")
        print("  • XAgent uses LIMITED internal agents (not full multi-agent)")
        print("  • Main Worker + User Interface + Mini-Agents (3-5 max)")
        print("  • Enables multi-tasking without architecture overhead")
        print("  • For full multi-agent systems, use XTeam")
        print()
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
