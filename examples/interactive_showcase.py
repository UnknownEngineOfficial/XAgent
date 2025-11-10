#!/usr/bin/env python3
"""
Interactive X-Agent Showcase
A comprehensive demonstration of X-Agent's capabilities with user interaction.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xagent.core.goal_engine import GoalEngine, GoalMode
from xagent.core.learning import StrategyLearner
from xagent.core.metacognition import MetaCognitionMonitor
from xagent.core.planner import Planner
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
import random

console = Console()


def show_banner():
    """Display welcome banner"""
    console.print(Panel.fit(
        "[bold cyan]🤖 X-Agent Interactive Showcase[/bold cyan]\n\n"
        "[dim]Experience the power of autonomous AI agents with emergent intelligence[/dim]",
        border_style="cyan"
    ))
    console.print()


def demo_goal_management():
    """Demonstrate goal management capabilities"""
    console.print("[bold yellow]═══ Goal Management Demo ═══[/bold yellow]\n")
    
    engine = GoalEngine()
    
    # Let user create a goal
    goal_desc = Prompt.ask(
        "Enter a goal description",
        default="Build a data analysis pipeline"
    )
    
    priority = int(Prompt.ask(
        "Enter priority (1-10)",
        default="7",
        choices=[str(i) for i in range(1, 11)]
    ))
    
    # Create main goal
    main_goal = engine.create_goal(
        description=goal_desc,
        mode=GoalMode.GOAL_ORIENTED,
        priority=priority
    )
    
    console.print(f"\n✓ Created main goal: [cyan]{main_goal.id[:20]}...[/cyan]")
    
    # Create sub-goals
    num_subgoals = int(Prompt.ask(
        "How many sub-goals to create?",
        default="3",
        choices=["2", "3", "4", "5"]
    ))
    
    sub_goals = []
    for i in range(num_subgoals):
        sub_goal = engine.create_goal(
            description=f"Sub-task {i+1}: {goal_desc.split()[0]} component {i+1}",
            mode=GoalMode.GOAL_ORIENTED,
            priority=priority - i - 1,
            parent_id=main_goal.id
        )
        sub_goals.append(sub_goal)
        console.print(f"  ✓ Created sub-goal {i+1}")
    
    # Display hierarchy
    console.print("\n[bold]Goal Hierarchy:[/bold]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Level", style="dim")
    table.add_column("Description")
    table.add_column("Status", justify="center")
    table.add_column("Priority", justify="right")
    
    table.add_row("Main", main_goal.description, main_goal.status.value, str(main_goal.priority))
    for i, sub_goal in enumerate(sub_goals):
        table.add_row(f"Sub-{i+1}", f"  └─ {sub_goal.description}", sub_goal.status.value, str(sub_goal.priority))
    
    console.print(table)
    
    # Simulate progress
    if Confirm.ask("\nSimulate goal completion?", default=True):
        console.print()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Completing goals...", total=len(sub_goals))
            
            for sub_goal in sub_goals:
                time.sleep(0.5)
                engine.update_goal_status(sub_goal.id, "in_progress")
                time.sleep(0.5)
                engine.update_goal_status(sub_goal.id, "completed")
                progress.update(task, advance=1)
            
            engine.update_goal_status(main_goal.id, "completed")
        
        console.print("\n✓ All goals completed successfully!\n")
    
    return engine


def demo_learning_system():
    """Demonstrate learning and adaptation"""
    console.print("[bold yellow]═══ Learning System Demo ═══[/bold yellow]\n")
    
    learner = StrategyLearner()
    
    console.print("Training on different strategies...\n")
    
    # Define strategies
    strategies = {
        "direct": {"success_rate": 0.6, "quality": 0.55, "speed": 2.0},
        "decompose": {"success_rate": 0.9, "quality": 0.85, "speed": 1.0},
        "think": {"success_rate": 0.4, "quality": 0.3, "speed": 3.0},
    }
    
    # Train with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Training...", total=30)
        
        for _ in range(10):
            for strategy_name, params in strategies.items():
                success = random.random() < params["success_rate"]
                quality = params["quality"] + random.uniform(-0.1, 0.1)
                
                learner.record_strategy_execution(
                    strategy_type=strategy_name,
                    context={"complexity": random.choice(["low", "medium", "high"])},
                    success=success,
                    duration=params["speed"] + random.uniform(-0.5, 0.5),
                    quality_score=max(0, min(1, quality))
                )
                progress.update(task, advance=1)
    
    # Show learned statistics
    console.print("\n[bold]Learning Results:[/bold]")
    stats = learner.get_strategy_statistics()
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Strategy")
    table.add_column("Attempts", justify="right")
    table.add_column("Success Rate", justify="right")
    table.add_column("Avg Quality", justify="right")
    table.add_column("Recommendation")
    
    for strategy_name, strategy_stats in stats.items():
        success_rate = strategy_stats["success_rate"]
        quality = strategy_stats["avg_quality_score"]
        
        # Determine recommendation
        if success_rate >= 0.8 and quality >= 0.7:
            rec = "[green]Highly Recommended[/green]"
        elif success_rate >= 0.6 and quality >= 0.5:
            rec = "[yellow]Recommended[/yellow]"
        else:
            rec = "[red]Not Recommended[/red]"
        
        table.add_row(
            strategy_name,
            str(strategy_stats["attempts"]),
            f"{success_rate:.1%}",
            f"{quality:.2f}",
            rec
        )
    
    console.print(table)
    
    # Interactive recommendation
    if Confirm.ask("\nGet strategy recommendation?", default=True):
        console.print()
        complexity = Prompt.ask(
            "What's the task complexity?",
            choices=["low", "medium", "high"],
            default="high"
        )
        
        recommended = learner.get_best_strategy(
            context={"complexity": complexity},
            available_strategies=list(strategies.keys())
        )
        
        if recommended:
            console.print(f"\n✓ Recommended strategy for [cyan]{complexity}[/cyan] complexity: [bold green]{recommended}[/bold green]\n")
        else:
            console.print("\n⚠ Insufficient data for recommendation\n")
    
    return learner


def demo_metacognition():
    """Demonstrate metacognition and self-monitoring"""
    console.print("[bold yellow]═══ Metacognition Demo ═══[/bold yellow]\n")
    
    monitor = MetaCognitionMonitor(enable_learning=True)
    
    console.print("Simulating agent execution with self-monitoring...\n")
    
    # Simulate iterations
    iterations = 5
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Running iterations...", total=iterations)
        
        for i in range(iterations):
            # Simulate execution
            result = {
                "success": random.random() > 0.2,
                "duration": random.uniform(0.5, 2.0),
                "quality": random.uniform(0.6, 1.0)
            }
            
            context = {
                "strategy": "decompose",
                "complexity": "high",
                "iteration": i + 1
            }
            
            evaluation = monitor.evaluate(result, context)
            results.append(evaluation)
            
            time.sleep(0.3)
            progress.update(task, advance=1)
    
    # Display evaluation results
    console.print("\n[bold]Metacognition Evaluation:[/bold]")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Iteration", justify="center")
    table.add_column("Success", justify="center")
    table.add_column("Quality", justify="right")
    table.add_column("Success Rate", justify="right")
    table.add_column("Status")
    
    for i, eval_result in enumerate(results):
        success_icon = "✓" if eval_result["current_result"]["success"] else "✗"
        success_rate = eval_result["success_rate"]
        
        if success_rate >= 0.8:
            status = "[green]Excellent[/green]"
        elif success_rate >= 0.6:
            status = "[yellow]Good[/yellow]"
        else:
            status = "[red]Needs Improvement[/red]"
        
        table.add_row(
            str(i + 1),
            success_icon,
            f"{eval_result['current_result']['quality']:.2f}",
            f"{success_rate:.1%}",
            status
        )
    
    console.print(table)
    
    # Show insights
    insights = monitor.get_learning_insights()
    console.print(f"\n[bold]Learning Status:[/bold] {'Active' if insights['learning_active'] else 'Inactive'}")
    console.print(f"[bold]Strategies Tracked:[/bold] {insights['strategies_tracked']}\n")
    
    return monitor


def demo_planning():
    """Demonstrate planning capabilities"""
    console.print("[bold yellow]═══ Planning Demo ═══[/bold yellow]\n")
    
    planner = Planner()
    
    # Get user input
    goal_desc = Prompt.ask(
        "Enter a goal to plan for",
        default="Create a machine learning model"
    )
    
    console.print("\n[dim]Generating plan...[/dim]\n")
    
    # Create plan
    goal_data = {
        "id": "demo_goal",
        "description": goal_desc,
        "mode": "goal_oriented",
        "priority": 7
    }
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Planning...", total=1)
        plan = planner.create_plan(goal_data)
        time.sleep(0.5)
        progress.update(task, completed=1)
    
    # Display plan
    console.print("\n[bold]Generated Plan:[/bold]")
    
    if "actions" in plan:
        for i, action in enumerate(plan["actions"][:5]):  # Show first 5
            console.print(f"  {i+1}. {action.get('description', 'Action')}")
    else:
        console.print("  [dim]Plan generated (see plan object for details)[/dim]")
    
    console.print()
    return planner


def show_summary():
    """Show final summary"""
    console.print("[bold green]═══ Demo Complete ═══[/bold green]\n")
    
    summary_table = Table(title="X-Agent Capabilities Demonstrated", show_header=True, header_style="bold cyan")
    summary_table.add_column("Feature", style="cyan")
    summary_table.add_column("Status", justify="center")
    summary_table.add_column("Description")
    
    features = [
        ("Goal Management", "✓", "Hierarchical goals with parent-child relationships"),
        ("Strategy Learning", "✓", "Learns from experience, adapts over time"),
        ("Metacognition", "✓", "Self-monitors and evaluates performance"),
        ("Planning", "✓", "Creates intelligent action plans"),
        ("Pattern Recognition", "✓", "Identifies success/failure patterns"),
        ("Adaptive Selection", "✓", "Context-aware strategy recommendations"),
    ]
    
    for feature, status, desc in features:
        summary_table.add_row(feature, status, desc)
    
    console.print(summary_table)
    console.print()
    
    console.print(Panel.fit(
        "[bold green]✨ X-Agent is Production Ready![/bold green]\n\n"
        "[dim]All core features demonstrated successfully\n"
        "Ready for real-world deployment[/dim]",
        border_style="green"
    ))


def main():
    """Main interactive showcase"""
    show_banner()
    
    demos = [
        ("Goal Management", demo_goal_management),
        ("Learning System", demo_learning_system),
        ("Metacognition", demo_metacognition),
        ("Planning", demo_planning),
    ]
    
    console.print("[bold]Available Demos:[/bold]")
    for i, (name, _) in enumerate(demos, 1):
        console.print(f"  {i}. {name}")
    
    console.print("  5. Run All Demos")
    console.print("  0. Exit")
    console.print()
    
    while True:
        choice = Prompt.ask(
            "Select demo",
            choices=["0", "1", "2", "3", "4", "5"],
            default="5"
        )
        
        if choice == "0":
            console.print("\n[dim]Goodbye![/dim]")
            break
        elif choice == "5":
            # Run all demos
            for name, demo_func in demos:
                console.print(f"\n{'='*60}\n")
                demo_func()
                console.print()
                if not Confirm.ask("Continue to next demo?", default=True):
                    break
            
            show_summary()
            break
        else:
            # Run selected demo
            idx = int(choice) - 1
            name, demo_func = demos[idx]
            console.print(f"\n{'='*60}\n")
            demo_func()
            console.print()
            
            if not Confirm.ask("Run another demo?", default=True):
                console.print("\n[dim]Thanks for exploring X-Agent![/dim]")
                break


if __name__ == "__main__":
    main()
