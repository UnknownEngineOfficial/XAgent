#!/usr/bin/env python3
"""
Example: Comparing Legacy and LangGraph Planners

This example demonstrates how to use both planners with X-Agent
and compare their behavior.
"""

import asyncio

from xagent.config import Settings
from xagent.core.agent import XAgent
from xagent.core.goal_engine import GoalMode


async def demo_legacy_planner():
    """Demonstrate the legacy planner."""
    print("\n" + "=" * 70)
    print("LEGACY PLANNER DEMO")
    print("=" * 70 + "\n")

    # Create agent with legacy planner (default)
    settings = Settings(use_langgraph_planner=False)
    agent = XAgent(settings=settings)

    print(f"✓ Agent created with planner: {agent.planner.__class__.__name__}")

    # Create a test goal
    goal = agent.goal_engine.create_goal(
        description="Write a Python function to calculate factorial",
        mode=GoalMode.GOAL_ORIENTED,
        priority=5,
    )

    print(f"✓ Goal created: {goal.id}")
    print(f"  Description: {goal.description}")

    # Create a plan using the legacy planner
    context = {
        "active_goal": goal.to_dict(),
        "memory_context": {"recent_actions": []},
    }

    plan = await agent.planner.create_plan(context)

    print("\n✓ Plan created by legacy planner:")
    if plan:
        print(f"  Type: {plan.get('type', 'N/A')}")
        print(f"  Action: {plan.get('action', 'N/A')}")
    else:
        print("  No plan generated")

    return plan


async def demo_langgraph_planner():
    """Demonstrate the LangGraph planner."""
    print("\n" + "=" * 70)
    print("LANGGRAPH PLANNER DEMO")
    print("=" * 70 + "\n")

    # Create agent with LangGraph planner
    settings = Settings(use_langgraph_planner=True)
    agent = XAgent(settings=settings)

    print(f"✓ Agent created with planner: {agent.planner.__class__.__name__}")

    # Create a test goal with completion criteria
    goal = agent.goal_engine.create_goal(
        description="Write a Python function to calculate factorial with tests",
        mode=GoalMode.GOAL_ORIENTED,
        priority=5,
        completion_criteria=[
            "Function is implemented",
            "Function handles edge cases",
            "Function has unit tests",
            "Code is documented",
        ],
    )

    print(f"✓ Goal created: {goal.id}")
    print(f"  Description: {goal.description}")
    print(f"  Completion criteria: {len(goal.completion_criteria)} items")

    # Create a plan using the LangGraph planner
    context = {
        "active_goal": goal.to_dict(),
        "memory_context": {"recent_actions": []},
    }

    plan = await agent.planner.create_plan(context)

    print("\n✓ Plan created by LangGraph planner:")
    if plan:
        print(f"  Type: {plan.get('type', 'N/A')}")
        print(f"  Action: {plan.get('action', 'N/A')}")
        print(f"  Goal Complexity: {plan.get('goal_complexity', 'N/A')}")
        print(f"  Quality Score: {plan.get('quality_score', 'N/A'):.2f}")
        print(f"  Remaining Actions: {plan.get('remaining_actions', 'N/A')}")
        if plan.get("sub_goals"):
            print(f"  Sub-goals: {len(plan['sub_goals'])}")
    else:
        print("  No plan generated")

    return plan


async def demo_agent_status():
    """Demonstrate agent status reporting."""
    print("\n" + "=" * 70)
    print("AGENT STATUS REPORTING")
    print("=" * 70 + "\n")

    # Mock memory to avoid actual initialization
    from unittest.mock import AsyncMock

    # Test with legacy planner
    print("1. Agent with Legacy Planner:")
    settings1 = Settings(use_langgraph_planner=False)
    agent1 = XAgent(settings=settings1)
    agent1.memory.initialize = AsyncMock()
    agent1.memory.close = AsyncMock()
    await agent1.initialize()

    status1 = await agent1.get_status()
    print(f"   Planner Type: {status1['planner_type']}")
    print(f"   Initialized: {status1['initialized']}")

    # Test with LangGraph planner
    print("\n2. Agent with LangGraph Planner:")
    settings2 = Settings(use_langgraph_planner=True)
    agent2 = XAgent(settings=settings2)
    agent2.memory.initialize = AsyncMock()
    agent2.memory.close = AsyncMock()
    await agent2.initialize()

    status2 = await agent2.get_status()
    print(f"   Planner Type: {status2['planner_type']}")
    print(f"   Initialized: {status2['initialized']}")


async def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("X-AGENT PLANNER COMPARISON DEMO")
    print("=" * 70)
    print("\nThis demo showcases the dual planner support in X-Agent.")
    print("You can switch between planners using the configuration setting.")

    # Demo legacy planner
    await demo_legacy_planner()

    # Demo LangGraph planner
    await demo_langgraph_planner()

    # Demo status reporting
    await demo_agent_status()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70 + "\n")

    print("Configuration Options:")
    print("  1. Environment variable: USE_LANGGRAPH_PLANNER=true/false")
    print("  2. Settings object: Settings(use_langgraph_planner=True/False)")
    print("  3. .env file: use_langgraph_planner=true/false")

    print("\nKey Differences:")
    print("  • Legacy Planner: Simple, rule-based, fast")
    print("  • LangGraph Planner: Multi-stage, complexity-aware, detailed")

    print("\nBoth planners:")
    print("  ✓ Use the same interface (create_plan)")
    print("  ✓ Work with the cognitive loop")
    print("  ✓ Return compatible plan formats")
    print("  ✓ Support all goal types")

    print("\n" + "=" * 70)
    print("Demo complete!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
