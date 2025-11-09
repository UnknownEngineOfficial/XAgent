"""
Example: Basic X-Agent usage

This example demonstrates how to:
1. Create and initialize an X-Agent
2. Set up a goal
3. Send commands
4. Monitor status
5. Clean shutdown
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xagent.core.agent import XAgent
from xagent.core.goal_engine import GoalMode


async def main():
    """Run basic X-Agent example."""
    print("=" * 60)
    print("X-Agent Basic Example")
    print("=" * 60)
    print()

    # Create agent
    print("1. Creating X-Agent...")
    agent = XAgent()

    # Initialize agent
    print("2. Initializing agent...")
    await agent.initialize()
    print("   ✓ Agent initialized")
    print()

    # Create a goal
    print("3. Creating a goal...")
    goal = agent.goal_engine.create_goal(
        description="Analyze system capabilities and prepare documentation",
        mode=GoalMode.GOAL_ORIENTED,
        priority=10,
        completion_criteria=[
            "System capabilities analyzed",
            "Documentation prepared",
        ],
    )
    print(f"   ✓ Goal created: {goal.id}")
    print(f"   Description: {goal.description}")
    print()

    # Start agent with goal
    print("4. Starting agent...")
    agent.goal_engine.set_active_goal(goal.id)

    # Note: In a real scenario, you would start the cognitive loop
    # For this example, we'll just demonstrate the API
    # await agent.start()

    # Get status
    print("5. Getting agent status...")
    status = await agent.get_status()
    print(f"   Initialized: {status['initialized']}")
    print(f"   Total goals: {status['goals_summary']['total']}")
    print(f"   Active goal: {goal.description[:50]}...")
    print()

    # Demonstrate sending commands (would be processed by cognitive loop)
    print("6. Sending commands (simulation)...")
    commands = [
        "List all available tools",
        "Check memory capacity",
        "Generate status report",
    ]

    for cmd in commands:
        print(f"   → {cmd}")
        # In real usage: await agent.send_command(cmd)
    print()

    # List all goals
    print("7. Listing all goals...")
    all_goals = agent.goal_engine.list_goals()
    for g in all_goals:
        print(f"   - [{g.status.value}] {g.description}")
    print()

    # Cleanup
    print("8. Cleaning up...")
    await agent.stop()
    print("   ✓ Agent stopped")
    print()

    print("=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
