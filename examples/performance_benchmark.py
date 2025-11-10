#!/usr/bin/env python3
"""
Performance Benchmark for X-Agent
Demonstrates real-world performance metrics
"""

import time
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xagent.core.goal_engine import GoalEngine, GoalMode
from xagent.core.learning import StrategyLearner
from xagent.core.metacognition import MetaCognitionMonitor
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
import random

console = Console()


def benchmark_goal_engine():
    """Benchmark goal engine performance"""
    console.print("\n[bold cyan]🎯 Goal Engine Performance Benchmark[/bold cyan]\n")
    
    engine = GoalEngine()
    
    # Benchmark: Goal Creation
    start = time.time()
    goals = []
    for i in range(100):
        goal = engine.create_goal(
            description=f"Test goal {i}",
            mode=GoalMode.GOAL_ORIENTED,
            priority=random.randint(1, 10)
        )
        goals.append(goal)
    creation_time = time.time() - start
    
    # Benchmark: Goal Retrieval
    start = time.time()
    for goal in goals:
        _ = engine.get_goal(goal.id)
    retrieval_time = time.time() - start
    
    # Benchmark: Goal Updates
    start = time.time()
    for goal in goals[:50]:
        engine.update_goal_status(goal.id, "in_progress")
    update_time = time.time() - start
    
    # Benchmark: Goal Completion
    start = time.time()
    for goal in goals[:50]:
        engine.update_goal_status(goal.id, "completed")
    completion_time = time.time() - start
    
    # Display results
    table = Table(title="Goal Engine Performance")
    table.add_column("Operation", style="cyan", no_wrap=True)
    table.add_column("Count", justify="right", style="magenta")
    table.add_column("Time (ms)", justify="right", style="green")
    table.add_column("Ops/sec", justify="right", style="yellow")
    
    table.add_row(
        "Goal Creation",
        "100",
        f"{creation_time * 1000:.2f}",
        f"{100 / creation_time:.2f}"
    )
    table.add_row(
        "Goal Retrieval",
        "100",
        f"{retrieval_time * 1000:.2f}",
        f"{100 / retrieval_time:.2f}"
    )
    table.add_row(
        "Goal Updates",
        "50",
        f"{update_time * 1000:.2f}",
        f"{50 / update_time:.2f}"
    )
    table.add_row(
        "Goal Completion",
        "50",
        f"{completion_time * 1000:.2f}",
        f"{50 / completion_time:.2f}"
    )
    
    console.print(table)
    
    return {
        "creation_ops_per_sec": 100 / creation_time,
        "retrieval_ops_per_sec": 100 / retrieval_time,
        "update_ops_per_sec": 50 / update_time,
        "completion_ops_per_sec": 50 / completion_time,
    }


def benchmark_strategy_learning():
    """Benchmark strategy learning performance"""
    console.print("\n[bold cyan]🧠 Strategy Learning Performance Benchmark[/bold cyan]\n")
    
    learner = StrategyLearner()
    
    # Benchmark: Recording Strategy Executions
    start = time.time()
    for i in range(1000):
        learner.record_strategy_execution(
            strategy_type=f"strategy_{i % 5}",
            context={"complexity": random.choice(["low", "medium", "high"])},
            success=random.random() > 0.3,
            duration=random.uniform(0.1, 2.0),
            quality_score=random.uniform(0.5, 1.0)
        )
    recording_time = time.time() - start
    
    # Benchmark: Getting Statistics
    start = time.time()
    for _ in range(100):
        _ = learner.get_strategy_statistics()
    stats_time = time.time() - start
    
    # Benchmark: Best Strategy Selection
    start = time.time()
    for _ in range(100):
        _ = learner.get_best_strategy(
            context={"complexity": "high"},
            available_strategies=[f"strategy_{i}" for i in range(5)]
        )
    selection_time = time.time() - start
    
    # Benchmark: Pattern Identification
    start = time.time()
    for _ in range(50):
        _ = learner.identify_patterns()
    pattern_time = time.time() - start
    
    # Display results
    table = Table(title="Strategy Learning Performance")
    table.add_column("Operation", style="cyan", no_wrap=True)
    table.add_column("Count", justify="right", style="magenta")
    table.add_column("Time (ms)", justify="right", style="green")
    table.add_column("Ops/sec", justify="right", style="yellow")
    
    table.add_row(
        "Record Execution",
        "1000",
        f"{recording_time * 1000:.2f}",
        f"{1000 / recording_time:.2f}"
    )
    table.add_row(
        "Get Statistics",
        "100",
        f"{stats_time * 1000:.2f}",
        f"{100 / stats_time:.2f}"
    )
    table.add_row(
        "Strategy Selection",
        "100",
        f"{selection_time * 1000:.2f}",
        f"{100 / selection_time:.2f}"
    )
    table.add_row(
        "Pattern Identification",
        "50",
        f"{pattern_time * 1000:.2f}",
        f"{50 / pattern_time:.2f}"
    )
    
    console.print(table)
    
    return {
        "recording_ops_per_sec": 1000 / recording_time,
        "stats_ops_per_sec": 100 / stats_time,
        "selection_ops_per_sec": 100 / selection_time,
        "pattern_ops_per_sec": 50 / pattern_time,
    }


def benchmark_metacognition():
    """Benchmark metacognition performance"""
    console.print("\n[bold cyan]🤔 Metacognition Performance Benchmark[/bold cyan]\n")
    
    monitor = MetaCognitionMonitor(enable_learning=True)
    
    # Benchmark: Evaluation
    start = time.time()
    for i in range(500):
        result = {
            "success": random.random() > 0.3,
            "duration": random.uniform(0.1, 2.0),
            "quality": random.uniform(0.5, 1.0)
        }
        context = {
            "strategy": f"strategy_{i % 5}",
            "complexity": random.choice(["low", "medium", "high"])
        }
        _ = monitor.evaluate(result, context)
    evaluation_time = time.time() - start
    
    # Benchmark: Get Insights
    start = time.time()
    for _ in range(100):
        _ = monitor.get_learning_insights()
    insights_time = time.time() - start
    
    # Benchmark: Strategy Recommendations
    start = time.time()
    for _ in range(100):
        _ = monitor.get_strategy_recommendation({"complexity": "high"})
    recommendation_time = time.time() - start
    
    # Display results
    table = Table(title="Metacognition Performance")
    table.add_column("Operation", style="cyan", no_wrap=True)
    table.add_column("Count", justify="right", style="magenta")
    table.add_column("Time (ms)", justify="right", style="green")
    table.add_column("Ops/sec", justify="right", style="yellow")
    
    table.add_row(
        "Evaluation",
        "500",
        f"{evaluation_time * 1000:.2f}",
        f"{500 / evaluation_time:.2f}"
    )
    table.add_row(
        "Get Insights",
        "100",
        f"{insights_time * 1000:.2f}",
        f"{100 / insights_time:.2f}"
    )
    table.add_row(
        "Recommendations",
        "100",
        f"{recommendation_time * 1000:.2f}",
        f"{100 / recommendation_time:.2f}"
    )
    
    console.print(table)
    
    return {
        "evaluation_ops_per_sec": 500 / evaluation_time,
        "insights_ops_per_sec": 100 / insights_time,
        "recommendation_ops_per_sec": 100 / recommendation_time,
    }


def main():
    """Run all benchmarks"""
    console.print(Panel.fit(
        "[bold yellow]X-Agent Performance Benchmark Suite[/bold yellow]\n"
        "[dim]Measuring real-world performance metrics[/dim]",
        border_style="yellow"
    ))
    
    # Run benchmarks
    goal_metrics = benchmark_goal_engine()
    learning_metrics = benchmark_strategy_learning()
    metacognition_metrics = benchmark_metacognition()
    
    # Summary
    console.print("\n[bold green]📊 Performance Summary[/bold green]\n")
    
    summary_table = Table(title="Overall Performance Metrics")
    summary_table.add_column("Component", style="cyan", no_wrap=True)
    summary_table.add_column("Avg Ops/sec", justify="right", style="green")
    summary_table.add_column("Performance", justify="right", style="yellow")
    
    goal_avg = sum(goal_metrics.values()) / len(goal_metrics)
    learning_avg = sum(learning_metrics.values()) / len(learning_metrics)
    metacog_avg = sum(metacognition_metrics.values()) / len(metacognition_metrics)
    
    def get_rating(ops_per_sec):
        if ops_per_sec > 1000:
            return "🚀 Excellent"
        elif ops_per_sec > 500:
            return "⚡ Very Good"
        elif ops_per_sec > 100:
            return "✓ Good"
        else:
            return "○ Acceptable"
    
    summary_table.add_row(
        "Goal Engine",
        f"{goal_avg:.2f}",
        get_rating(goal_avg)
    )
    summary_table.add_row(
        "Strategy Learning",
        f"{learning_avg:.2f}",
        get_rating(learning_avg)
    )
    summary_table.add_row(
        "Metacognition",
        f"{metacog_avg:.2f}",
        get_rating(metacog_avg)
    )
    
    overall_avg = (goal_avg + learning_avg + metacog_avg) / 3
    summary_table.add_row(
        "[bold]Overall Average[/bold]",
        f"[bold]{overall_avg:.2f}[/bold]",
        f"[bold]{get_rating(overall_avg)}[/bold]"
    )
    
    console.print(summary_table)
    
    # Final message
    console.print(Panel.fit(
        "[bold green]✓ All benchmarks completed successfully![/bold green]\n\n"
        f"[dim]Overall Performance: {overall_avg:.2f} operations/second[/dim]\n"
        f"[dim]Rating: {get_rating(overall_avg)}[/dim]",
        border_style="green"
    ))
    
    return {
        "goal_engine": goal_metrics,
        "strategy_learning": learning_metrics,
        "metacognition": metacognition_metrics,
        "overall_average": overall_avg
    }


if __name__ == "__main__":
    results = main()
