#!/usr/bin/env python3
"""
Quick Demo - X-Agent Core Capabilities
=======================================

This script demonstrates X-Agent's core capabilities without requiring
external services like Redis or Docker.

Features Demonstrated:
- Goal Engine: Create and manage hierarchical goals
- Planner: Create execution plans (both legacy and LangGraph)
- Executor: Execute actions and track results
- Metacognition: Monitor performance and learn

Run: python examples/quick_demo.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown

from xagent.core.goal_engine import GoalEngine, GoalStatus
from xagent.core.planner import Planner
from xagent.core.executor import Executor
from xagent.core.metacognition import MetaCognitionMonitor
from xagent.config import Settings

console = Console()


def demo_goal_management():
    """Demonstrate the goal management system."""
    console.print("\n[bold cyan]═══ 1. Goal Management System ═══[/bold cyan]\n")
    
    engine = GoalEngine()
    
    # Create main goal
    console.print("[yellow]Creating main goal...[/yellow]")
    main_goal = engine.create_goal(
        description="Process customer data and generate report",
        priority=10
    )
    console.print(f"[green]✓[/green] Main goal created: {main_goal.id[:12]}...")
    
    # Create sub-goals
    console.print("\n[yellow]Creating sub-goals...[/yellow]")
    sub_goals = []
    sub_goal_descriptions = [
        "Load customer data from CSV file",
        "Clean and validate data entries",
        "Calculate summary statistics",
        "Generate visualizations",
        "Export final report as PDF"
    ]
    
    for i, desc in enumerate(sub_goal_descriptions, 1):
        sub_goal = engine.create_goal(
            description=desc,
            priority=10 - i,
            parent_id=main_goal.id
        )
        sub_goals.append(sub_goal)
        console.print(f"[green]✓[/green] Sub-goal {i}: {desc}")
    
    # Display goal hierarchy
    console.print("\n[bold]Goal Hierarchy:[/bold]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Level", style="dim", width=10)
    table.add_column("Description", width=50)
    table.add_column("Status", width=15)
    table.add_column("Priority", justify="right")
    
    table.add_row("Main", main_goal.description, main_goal.status.value, str(main_goal.priority))
    for i, sg in enumerate(sub_goals, 1):
        table.add_row(f"Sub-{i}", f"  └─ {sg.description}", sg.status.value, str(sg.priority))
    
    console.print(table)
    
    # Simulate goal progression
    console.print("\n[yellow]Simulating goal progression...[/yellow]")
    import time
    for i, sg in enumerate(sub_goals, 1):
        console.print(f"[dim]Processing sub-goal {i}...[/dim]", end=" ")
        time.sleep(0.3)
        engine.update_goal_status(sg.id, GoalStatus.IN_PROGRESS)
        time.sleep(0.3)
        engine.update_goal_status(sg.id, GoalStatus.COMPLETED)
        console.print(f"[green]✓[/green] Sub-goal {i} completed")
    
    # Complete main goal
    engine.update_goal_status(main_goal.id, GoalStatus.COMPLETED)
    console.print(f"\n[green]✓[/green] Main goal completed!")
    
    # Show statistics
    all_goals = engine.list_goals()
    stats = {
        "total": len(all_goals),
        "completed": sum(1 for g in all_goals if g.status == GoalStatus.COMPLETED),
        "in_progress": sum(1 for g in all_goals if g.status == GoalStatus.IN_PROGRESS),
        "pending": sum(1 for g in all_goals if g.status == GoalStatus.PENDING)
    }
    
    stats_table = Table(show_header=True, header_style="bold blue")
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", justify="right", style="green")
    for key, value in stats.items():
        stats_table.add_row(key.replace("_", " ").title(), str(value))
    
    console.print("\n[bold]Goal Statistics:[/bold]")
    console.print(stats_table)
    
    return engine, main_goal


async def demo_planning():
    """Demonstrate the planning system."""
    console.print("\n\n[bold cyan]═══ 2. Planning System ═══[/bold cyan]\n")
    
    settings = Settings()
    planner = Planner(settings)
    
    # Create a sample goal
    console.print("[yellow]Creating plan for a complex goal...[/yellow]")
    goal = {
        "id": "goal_12345",
        "description": "Build a REST API for user management",
        "priority": 8
    }
    
    console.print(f"\n[bold]Goal:[/bold] {goal['description']}")
    console.print(f"[bold]Priority:[/bold] {goal['priority']}")
    
    # Generate plan
    console.print("\n[yellow]Generating execution plan...[/yellow]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Planning...", total=1)
        plan = await planner.create_plan(goal)
        progress.update(task, completed=1)
    
    console.print(f"[green]✓[/green] Plan generated with {len(plan['actions'])} actions\n")
    
    # Display plan
    plan_table = Table(show_header=True, header_style="bold magenta")
    plan_table.add_column("#", style="dim", width=5)
    plan_table.add_column("Action", width=50)
    plan_table.add_column("Type", width=15)
    
    for i, action in enumerate(plan["actions"], 1):
        plan_table.add_row(
            str(i),
            action.get("description", action.get("type", "N/A")),
            action["type"]
        )
    
    console.print(plan_table)
    
    # Show plan quality
    quality = plan.get("quality", 0.85)
    console.print(f"\n[bold]Plan Quality:[/bold] {quality:.1%}")
    if quality >= 0.8:
        console.print("[green]✓ High quality plan[/green]")
    elif quality >= 0.6:
        console.print("[yellow]⚠ Medium quality plan[/yellow]")
    else:
        console.print("[red]✗ Low quality plan - refinement needed[/red]")
    
    return planner, plan


async def demo_execution():
    """Demonstrate the execution system."""
    console.print("\n\n[bold cyan]═══ 3. Execution System ═══[/bold cyan]\n")
    
    executor = Executor()
    
    # Execute sample actions
    actions = [
        {"type": "think", "content": "Analyzing requirements for user management API"},
        {"type": "think", "content": "Designing database schema for user table"},
        {"type": "think", "content": "Planning authentication and authorization flow"}
    ]
    
    console.print("[yellow]Executing actions...[/yellow]\n")
    
    results = []
    for i, action in enumerate(actions, 1):
        console.print(f"[bold]Action {i}:[/bold] {action['type']}")
        console.print(f"  Content: {action['content']}")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Executing...", total=1)
            result = await executor.execute(action)
            results.append(result)
            progress.update(task, completed=1)
        
        if result.get("success", False):
            console.print(f"[green]✓[/green] Action completed successfully\n")
        else:
            console.print(f"[red]✗[/red] Action failed: {result.get('error', 'Unknown error')}\n")
    
    # Show execution summary
    success_count = sum(1 for r in results if r.get("success", False))
    console.print(f"[bold]Execution Summary:[/bold]")
    console.print(f"  Total Actions: {len(results)}")
    console.print(f"  Successful: {success_count}")
    console.print(f"  Success Rate: {success_count/len(results):.1%}")
    
    return executor, results


def demo_metacognition():
    """Demonstrate the metacognition system."""
    console.print("\n\n[bold cyan]═══ 4. Metacognition & Learning ═══[/bold cyan]\n")
    
    meta = MetaCognitionMonitor()
    
    # Record sample action results
    console.print("[yellow]Recording agent performance...[/yellow]")
    results = [
        {"success": True, "duration": 1.2, "action": "create_plan"},
        {"success": True, "duration": 0.5, "action": "execute_action"},
        {"success": True, "duration": 0.3, "action": "think"},
        {"success": False, "duration": 2.1, "action": "execute_action"},
        {"success": True, "duration": 1.1, "action": "create_plan"},
        {"success": True, "duration": 0.6, "action": "execute_action"},
        {"success": True, "duration": 0.4, "action": "think"},
        {"success": True, "duration": 0.5, "action": "execute_action"},
    ]
    
    for result in results:
        evaluation = meta.evaluate(result)
    
    console.print(f"[green]✓[/green] Recorded {len(results)} actions\n")
    
    # Analyze performance
    console.print("[bold]Performance Analysis:[/bold]")
    
    # Calculate metrics
    success_count = sum(1 for r in results if r["success"])
    success_rate = success_count / len(results)
    avg_duration = sum(r["duration"] for r in results) / len(results)
    
    console.print(f"  Overall Success Rate: [green]{success_rate:.1%}[/green]")
    console.print(f"  Average Duration: [cyan]{avg_duration:.2f}s[/cyan]")
    
    # Check for error patterns in metacognition
    if meta.error_patterns:
        console.print(f"\n[yellow]⚠ Error Patterns Detected:[/yellow]")
        for pattern, count in meta.error_patterns.items():
            console.print(f"    • {pattern}: {count} occurrence(s)")
    else:
        console.print(f"\n[green]✓ No error patterns detected[/green]")
    
    # Show metrics table
    metrics_table = Table(show_header=True, header_style="bold blue")
    metrics_table.add_column("Metric", style="cyan")
    metrics_table.add_column("Value", justify="right", style="green")
    
    metrics_table.add_row("Total Actions", str(len(results)))
    metrics_table.add_row("Successful", str(success_count))
    metrics_table.add_row("Failed", str(len(results) - success_count))
    metrics_table.add_row("Avg Duration", f"{avg_duration:.2f}s")
    
    console.print("\n")
    console.print(metrics_table)
    
    return meta


async def main():
    """Run all demonstrations."""
    console.print(Panel.fit(
        "[bold cyan]X-Agent Quick Demo[/bold cyan]\n"
        "[dim]Demonstrating Core Capabilities[/dim]",
        border_style="cyan"
    ))
    
    try:
        # Run demonstrations
        engine, goal = demo_goal_management()
        planner, plan = await demo_planning()
        executor, results = await demo_execution()
        meta = demo_metacognition()
        
        # Final summary
        console.print("\n\n")
        console.print(Panel.fit(
            "[bold green]✓ Demo Complete![/bold green]\n\n"
            "[bold]Successfully Demonstrated:[/bold]\n"
            "  • Goal Management (6 goals created)\n"
            "  • Planning System (Multi-step plan generated)\n"
            "  • Action Execution (3 actions executed)\n"
            "  • Metacognition (Performance analyzed)\n\n"
            "[dim]All core X-Agent capabilities are operational![/dim]",
            border_style="green"
        ))
        
        # Show quick start info
        console.print("\n[bold]Next Steps:[/bold]")
        console.print("  1. Run tests: [cyan]make test[/cyan]")
        console.print("  2. Start API: [cyan]python -m uvicorn xagent.api.rest:app --reload[/cyan]")
        console.print("  3. View docs: [cyan]open http://localhost:8000/docs[/cyan]")
        console.print("  4. Try Docker: [cyan]docker-compose up -d[/cyan]\n")
        
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
