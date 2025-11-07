"""
Example: Goal Management

This example demonstrates:
1. Creating different types of goals
2. Goal hierarchy (parent/child goals)
3. Goal status tracking
4. Priority-based scheduling
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xagent.core.goal_engine import GoalEngine, GoalMode, GoalStatus


async def main():
    """Demonstrate goal management."""
    print("=" * 60)
    print("X-Agent Goal Management Example")
    print("=" * 60)
    print()
    
    engine = GoalEngine()
    
    # 1. Create a goal-oriented task
    print("1. Creating goal-oriented task...")
    project_goal = engine.create_goal(
        description="Build a web application",
        mode=GoalMode.GOAL_ORIENTED,
        priority=10,
        completion_criteria=[
            "Backend API implemented",
            "Frontend UI created",
            "Tests written and passing",
            "Documentation complete",
        ],
    )
    print(f"   ✓ Created: {project_goal.description}")
    print()
    
    # 2. Create sub-goals
    print("2. Breaking down into sub-goals...")
    backend_goal = engine.create_goal(
        description="Implement backend API",
        parent_id=project_goal.id,
        priority=8,
        completion_criteria=["REST endpoints", "Database models", "Authentication"],
    )
    
    frontend_goal = engine.create_goal(
        description="Create frontend UI",
        parent_id=project_goal.id,
        priority=7,
        completion_criteria=["React components", "State management", "Routing"],
    )
    
    testing_goal = engine.create_goal(
        description="Write tests",
        parent_id=project_goal.id,
        priority=6,
    )
    
    print(f"   ✓ Backend: {backend_goal.description}")
    print(f"   ✓ Frontend: {frontend_goal.description}")
    print(f"   ✓ Testing: {testing_goal.description}")
    print()
    
    # 3. Create a continuous task
    print("3. Creating continuous monitoring task...")
    monitor_goal = engine.create_goal(
        description="Monitor system health and performance",
        mode=GoalMode.CONTINUOUS,
        priority=5,
    )
    print(f"   ✓ Created continuous task: {monitor_goal.description}")
    print()
    
    # 4. Show goal hierarchy
    print("4. Goal hierarchy:")
    hierarchy = engine.get_goal_hierarchy(project_goal.id)
    print(f"   Main Goal: {hierarchy['goal']['description']}")
    print(f"   Sub-goals:")
    for sub in hierarchy['sub_goals']:
        print(f"     - {sub['goal']['description']}")
    print()
    
    # 5. Get next goal to work on
    print("5. Getting next goal by priority...")
    next_goal = engine.get_next_goal()
    if next_goal:
        print(f"   Next goal: {next_goal.description}")
        print(f"   Priority: {next_goal.priority}")
    print()
    
    # 6. Simulate progress
    print("6. Simulating progress...")
    engine.set_active_goal(backend_goal.id)
    print(f"   Started: {backend_goal.description}")
    
    engine.update_goal_status(backend_goal.id, GoalStatus.COMPLETED)
    print(f"   ✓ Completed: {backend_goal.description}")
    print()
    
    # 7. Check completion status
    print("7. Checking completion status...")
    print(f"   Backend completed: {engine.check_goal_completion(backend_goal.id)}")
    print(f"   Project completed: {engine.check_goal_completion(project_goal.id)}")
    print(f"   Monitor completed: {engine.check_goal_completion(monitor_goal.id)} (continuous)")
    print()
    
    # 8. List goals by status
    print("8. Goals by status:")
    
    pending = engine.list_goals(status=GoalStatus.PENDING)
    completed = engine.list_goals(status=GoalStatus.COMPLETED)
    
    print(f"   Pending ({len(pending)}):")
    for g in pending:
        print(f"     - {g.description}")
    
    print(f"   Completed ({len(completed)}):")
    for g in completed:
        print(f"     - {g.description}")
    print()
    
    print("=" * 60)
    print("Goal management example completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
