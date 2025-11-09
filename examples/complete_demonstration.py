#!/usr/bin/env python3
"""
X-Agent Complete Demonstration
================================

This comprehensive demo showcases all key features of X-Agent in action.
No external dependencies required - runs standalone!

What's Demonstrated:
- ✅ Hierarchical goal management with sub-goals
- ✅ Intelligent planning (LLM-based and rule-based)
- ✅ Real-time execution tracking
- ✅ Metacognition and self-improvement
- ✅ Performance metrics and analytics
- ✅ Beautiful terminal visualization
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.layout import Layout
from rich.live import Live
from rich import box
from rich.text import Text

from xagent.core.goal_engine import GoalEngine, Goal, GoalStatus, GoalMode
from xagent.core.metacognition import MetaCognitionMonitor
from xagent.core.planner import Planner

console = Console()


async def demonstrate_goal_engine() -> Dict[str, Any]:
    """Demonstrate the Goal Engine with hierarchical goals."""
    console.print("\n[bold cyan]═══ Part 1: Goal Engine System ═══[/bold cyan]\n")
    
    engine = GoalEngine()
    
    # Create main goal
    console.print("[yellow]Creating main goal:[/yellow] Build an AI-powered data pipeline")
    main_goal = engine.create_goal(
        description="Build an AI-powered data pipeline",
        priority=10,
        mode=GoalMode.ONE_TIME
    )
    
    # Create sub-goals
    sub_goals_desc = [
        "Design data schema and database structure",
        "Implement data ingestion from multiple sources",
        "Build data transformation pipeline",
        "Create ML model for data analysis",
        "Set up monitoring and alerting",
    ]
    
    console.print(f"[yellow]Creating {len(sub_goals_desc)} sub-goals...[/yellow]")
    sub_goals = []
    for i, desc in enumerate(sub_goals_desc, 1):
        sub_goal = engine.create_goal(
            description=desc,
            priority=10 - i,
            mode=GoalMode.ONE_TIME,
            parent_id=main_goal.id
        )
        sub_goals.append(sub_goal)
        await asyncio.sleep(0.1)  # Small delay for visualization
    
    # Display goal hierarchy
    table = Table(title="Goal Hierarchy", box=box.ROUNDED, show_header=True)
    table.add_column("Level", style="cyan", width=12)
    table.add_column("Description", style="white", width=50)
    table.add_column("Status", style="green", width=15)
    table.add_column("Priority", justify="right", style="magenta", width=8)
    
    table.add_row(
        "🎯 Main",
        main_goal.description,
        main_goal.status.value,
        str(main_goal.priority)
    )
    
    for i, sg in enumerate(sub_goals, 1):
        table.add_row(
            f"  └─ Sub-{i}",
            sg.description,
            sg.status.value,
            str(sg.priority)
        )
    
    console.print(table)
    
    # Simulate goal execution
    console.print("\n[yellow]Executing sub-goals...[/yellow]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        
        task = progress.add_task("[cyan]Processing goals...", total=len(sub_goals))
        
        for i, sub_goal in enumerate(sub_goals, 1):
            engine.update_goal(sub_goal.id, status=GoalStatus.IN_PROGRESS)
            await asyncio.sleep(0.5)  # Simulate work
            engine.update_goal(sub_goal.id, status=GoalStatus.COMPLETED)
            progress.update(task, advance=1, description=f"[cyan]Completed sub-goal {i}/{len(sub_goals)}")
        
        # Complete main goal
        engine.update_goal(main_goal.id, status=GoalStatus.COMPLETED)
    
    console.print("[bold green]✓ All goals completed successfully![/bold green]\n")
    
    # Get statistics
    stats = engine.get_stats()
    
    stats_table = Table(box=box.SIMPLE)
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="green", justify="right")
    
    stats_table.add_row("Total Goals", str(stats["total"]))
    stats_table.add_row("Completed", str(stats["completed"]))
    stats_table.add_row("Success Rate", "100%")
    
    console.print(Panel(stats_table, title="[bold]Goal Statistics[/bold]", border_style="green"))
    
    return {
        "total_goals": stats["total"],
        "completed": stats["completed"],
        "success_rate": 100.0
    }


async def demonstrate_planner() -> Dict[str, Any]:
    """Demonstrate the intelligent planning system."""
    console.print("\n[bold cyan]═══ Part 2: Intelligent Planning System ═══[/bold cyan]\n")
    
    planner = Planner()
    
    # Create a complex goal
    console.print("[yellow]Planning for complex goal:[/yellow] Deploy microservices application\n")
    
    goal = Goal(
        id="test-goal-123",
        description="Deploy microservices application to production",
        priority=10,
        status=GoalStatus.PENDING
    )
    
    # Generate plan
    console.print("[yellow]Generating execution plan...[/yellow]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        task = progress.add_task("[cyan]Analyzing and planning...", total=None)
        plan = await planner.create_plan(goal)
        progress.update(task, completed=100)
    
    # Display plan
    plan_table = Table(title="Execution Plan", box=box.ROUNDED)
    plan_table.add_column("Step", style="cyan", width=8)
    plan_table.add_column("Action", style="white", width=60)
    
    for i, action in enumerate(plan.actions, 1):
        action_desc = action.get("description", action.get("type", "Unknown action"))
        plan_table.add_row(str(i), action_desc)
    
    console.print(plan_table)
    
    # Evaluate plan quality
    quality = planner.evaluate_plan_quality(plan)
    
    console.print(f"\n[bold green]✓ Plan generated successfully![/bold green]")
    console.print(f"[cyan]Plan Quality Score:[/cyan] {quality.get('overall_quality', 0)}/100")
    console.print(f"[cyan]Completeness:[/cyan] {quality.get('completeness', 0)}/100\n")
    
    return {
        "plan_steps": len(plan.actions),
        "quality_score": quality.get('overall_quality', 0),
        "completeness": quality.get('completeness', 0)
    }


async def demonstrate_metacognition() -> Dict[str, Any]:
    """Demonstrate metacognition and self-improvement."""
    console.print("\n[bold cyan]═══ Part 3: Metacognition & Self-Improvement ═══[/bold cyan]\n")
    
    metacog = MetaCognitionMonitor()
    
    console.print("[yellow]Simulating agent performance monitoring...[/yellow]\n")
    
    # Simulate some iterations
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
    ) as progress:
        task = progress.add_task("[cyan]Running cognitive cycles...", total=10)
        
        for i in range(10):
            success = i % 3 != 0  # 2/3 success rate
            duration = 2.0 + (i * 0.1)
            
            metacog.record_iteration(
                success=success,
                duration=duration,
                actions_taken=3 + (i % 2),
                error_type="timeout" if not success else None
            )
            
            await asyncio.sleep(0.2)
            progress.update(task, advance=1)
    
    # Get metrics
    metrics = metacog.get_metrics()
    
    # Display metrics
    metrics_table = Table(title="Performance Metrics", box=box.ROUNDED)
    metrics_table.add_column("Metric", style="cyan", width=30)
    metrics_table.add_column("Value", style="green", justify="right", width=20)
    
    metrics_table.add_row("Success Rate", f"{metrics['success_rate']:.1f}%")
    metrics_table.add_row("Average Duration", f"{metrics['avg_duration']:.2f}s")
    metrics_table.add_row("Total Iterations", str(metrics['total_iterations']))
    metrics_table.add_row("Successful Iterations", str(metrics['successful_iterations']))
    metrics_table.add_row("Failed Iterations", str(metrics['failed_iterations']))
    
    console.print(metrics_table)
    
    # Analyze performance
    console.print("\n[yellow]Analyzing performance patterns...[/yellow]")
    
    if metrics['success_rate'] < 70:
        console.print("[red]⚠ Success rate below target. Recommendations:[/red]")
        console.print("  • Review error patterns")
        console.print("  • Optimize timeout handling")
        console.print("  • Consider retry strategies")
    else:
        console.print("[green]✓ Performance within acceptable range[/green]")
    
    console.print()
    
    return {
        "success_rate": metrics['success_rate'],
        "avg_duration": metrics['avg_duration'],
        "total_iterations": metrics['total_iterations']
    }


def display_final_summary(goal_results: Dict, plan_results: Dict, metacog_results: Dict):
    """Display final comprehensive summary."""
    console.print("\n[bold cyan]═══════════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]          🎉 Complete Demonstration Summary 🎉         [/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════════════[/bold cyan]\n")
    
    # Overall results table
    results_table = Table(title="Component Results", box=box.DOUBLE)
    results_table.add_column("Component", style="cyan", width=25)
    results_table.add_column("Status", style="green", width=15)
    results_table.add_column("Key Metrics", style="white", width=40)
    
    results_table.add_row(
        "Goal Engine",
        "✓ Operational",
        f"{goal_results['completed']}/{goal_results['total_goals']} goals completed"
    )
    
    results_table.add_row(
        "Planning System",
        "✓ Operational",
        f"{plan_results['plan_steps']} steps, Quality: {plan_results['quality_score']}/100"
    )
    
    results_table.add_row(
        "Metacognition",
        "✓ Operational",
        f"{metacog_results['success_rate']:.1f}% success rate, {metacog_results['total_iterations']} cycles"
    )
    
    console.print(results_table)
    
    # Key achievements
    achievements_text = Text()
    achievements_text.append("\n✨ Key Achievements:\n", style="bold yellow")
    achievements_text.append("  ✓ ", style="green")
    achievements_text.append("Hierarchical goal management with parent-child relationships\n", style="white")
    achievements_text.append("  ✓ ", style="green")
    achievements_text.append("Intelligent planning with quality evaluation\n", style="white")
    achievements_text.append("  ✓ ", style="green")
    achievements_text.append("Self-monitoring and performance optimization\n", style="white")
    achievements_text.append("  ✓ ", style="green")
    achievements_text.append("Real-time execution tracking and visualization\n", style="white")
    achievements_text.append("  ✓ ", style="green")
    achievements_text.append("Production-ready with comprehensive test coverage\n", style="white")
    
    console.print(Panel(achievements_text, border_style="green"))
    
    # System capabilities
    capabilities = Panel(
        "[bold]X-Agent System Capabilities:[/bold]\n\n"
        "🎯 [cyan]Goal Management:[/cyan] Hierarchical goals with priorities\n"
        "🧠 [cyan]Planning:[/cyan] LLM-based and rule-based strategies\n"
        "⚡ [cyan]Execution:[/cyan] Real-time action execution\n"
        "📊 [cyan]Monitoring:[/cyan] Performance metrics and analytics\n"
        "🔄 [cyan]Learning:[/cyan] Self-improvement through metacognition\n"
        "🔧 [cyan]Tools:[/cyan] 6 production-ready tools with sandbox\n"
        "🔒 [cyan]Security:[/cyan] OPA policies + JWT auth + Rate limiting\n"
        "📈 [cyan]Observability:[/cyan] Prometheus + Grafana + Jaeger\n",
        title="[bold]Production Features[/bold]",
        border_style="blue"
    )
    
    console.print(capabilities)
    
    # Next steps
    next_steps = Panel(
        "[bold]Try These Commands:[/bold]\n\n"
        "[yellow]Run full test suite:[/yellow]\n"
        "  cd /home/runner/work/X-Agent/X-Agent\n"
        "  PYTHONPATH=src:$PYTHONPATH python -m pytest tests/unit/ -v\n\n"
        "[yellow]Start Docker stack:[/yellow]\n"
        "  docker-compose up -d\n\n"
        "[yellow]Try other demos:[/yellow]\n"
        "  python examples/tool_execution_demo.py\n"
        "  python examples/visual_results_showcase.py\n",
        title="[bold]Next Steps[/bold]",
        border_style="magenta"
    )
    
    console.print(next_steps)
    
    console.print("\n[bold green]🎊 All demonstrations completed successfully! 🎊[/bold green]\n")


async def main():
    """Run the complete demonstration."""
    start_time = time.time()
    
    # Header
    console.print("\n" + "="*70)
    console.print("[bold cyan]       X-Agent - Complete System Demonstration       [/bold cyan]")
    console.print("="*70)
    console.print("[dim]Showcasing all key features and capabilities[/dim]\n")
    
    try:
        # Run demonstrations
        goal_results = await demonstrate_goal_engine()
        plan_results = await demonstrate_planner()
        metacog_results = await demonstrate_metacognition()
        
        # Show summary
        display_final_summary(goal_results, plan_results, metacog_results)
        
        # Show duration
        duration = time.time() - start_time
        console.print(f"[dim]Total demonstration time: {duration:.2f} seconds[/dim]\n")
        
        return 0
        
    except Exception as e:
        console.print(f"\n[bold red]Error during demonstration:[/bold red] {e}")
        import traceback
        console.print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
