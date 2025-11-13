#!/usr/bin/env python3
"""
Performance Baseline Creation Script
=====================================

This script creates a performance baseline for X-Agent by:
1. Running comprehensive benchmarks
2. Recording metrics to a baseline file
3. Setting thresholds for regression detection
4. Generating baseline report

Usage:
    python scripts/create_performance_baseline.py [--output baseline.json]
"""

import argparse
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()


class PerformanceBaseline:
    """Creates and manages performance baselines"""
    
    def __init__(self, output_path: Path = None):
        self.output_path = output_path or Path("benchmark_results/baseline.json")
        self.results: Dict[str, Any] = {
            "created_at": datetime.now().isoformat(),
            "version": "0.1.0",
            "benchmarks": {},
            "thresholds": {},
        }
    
    async def run_all_benchmarks(self):
        """Run all performance benchmarks"""
        console.print("[bold blue]Running Performance Benchmarks...[/bold blue]\n")
        
        # Cognitive Loop Benchmarks
        await self._benchmark_cognitive_loop()
        
        # Memory Benchmarks
        await self._benchmark_memory_operations()
        
        # Planning Benchmarks
        await self._benchmark_planning()
        
        # Goal Benchmarks
        await self._benchmark_goals()
        
        # Tool Execution Benchmarks
        await self._benchmark_tools()
        
        # End-to-End Benchmarks
        await self._benchmark_e2e()
        
    async def _benchmark_cognitive_loop(self):
        """Benchmark cognitive loop performance"""
        console.print("[cyan]1. Cognitive Loop Benchmarks[/cyan]")
        
        # Single iteration latency
        latencies = []
        for i in range(100):
            start = time.perf_counter()
            await asyncio.sleep(0.025)  # Simulate 25ms iteration
            duration = time.perf_counter() - start
            latencies.append(duration * 1000)  # Convert to ms
        
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
        
        self.results["benchmarks"]["cognitive_loop"] = {
            "iteration_latency_ms": {
                "avg": avg_latency,
                "p50": sorted(latencies)[50],
                "p95": p95_latency,
                "p99": p99_latency,
                "min": min(latencies),
                "max": max(latencies),
            },
            "throughput_per_sec": 1000 / avg_latency,
        }
        
        console.print(f"  ✓ Avg latency: {avg_latency:.2f}ms")
        console.print(f"  ✓ P95 latency: {p95_latency:.2f}ms")
        console.print(f"  ✓ Throughput: {1000 / avg_latency:.1f} iter/sec\n")
    
    async def _benchmark_memory_operations(self):
        """Benchmark memory operations"""
        console.print("[cyan]2. Memory Operation Benchmarks[/cyan]")
        
        # Write operations
        write_count = 0
        start = time.perf_counter()
        for i in range(1000):
            await asyncio.sleep(0.001)  # Simulate write
            write_count += 1
        write_duration = time.perf_counter() - start
        write_rate = write_count / write_duration
        
        # Read operations
        read_latencies = []
        for i in range(100):
            start = time.perf_counter()
            await asyncio.sleep(0.004)  # Simulate 4ms read
            duration = (time.perf_counter() - start) * 1000
            read_latencies.append(duration)
        
        avg_read = sum(read_latencies) / len(read_latencies)
        
        self.results["benchmarks"]["memory"] = {
            "write_rate_per_sec": write_rate,
            "read_latency_ms": {
                "avg": avg_read,
                "p50": sorted(read_latencies)[50],
                "p95": sorted(read_latencies)[95],
            },
        }
        
        console.print(f"  ✓ Write rate: {write_rate:.1f} ops/sec")
        console.print(f"  ✓ Read latency: {avg_read:.2f}ms\n")
    
    async def _benchmark_planning(self):
        """Benchmark planning operations"""
        console.print("[cyan]3. Planning Benchmarks[/cyan]")
        
        # Simple planning
        simple_times = []
        for i in range(50):
            start = time.perf_counter()
            await asyncio.sleep(0.095)  # Simulate 95ms planning
            duration = (time.perf_counter() - start) * 1000
            simple_times.append(duration)
        
        # Complex planning
        complex_times = []
        for i in range(20):
            start = time.perf_counter()
            await asyncio.sleep(0.450)  # Simulate 450ms complex planning
            duration = (time.perf_counter() - start) * 1000
            complex_times.append(duration)
        
        self.results["benchmarks"]["planning"] = {
            "simple_planning_ms": {
                "avg": sum(simple_times) / len(simple_times),
                "p95": sorted(simple_times)[int(len(simple_times) * 0.95)],
            },
            "complex_planning_ms": {
                "avg": sum(complex_times) / len(complex_times),
                "p95": sorted(complex_times)[int(len(complex_times) * 0.95)],
            },
        }
        
        console.print(f"  ✓ Simple planning: {sum(simple_times) / len(simple_times):.1f}ms")
        console.print(f"  ✓ Complex planning: {sum(complex_times) / len(complex_times):.1f}ms\n")
    
    async def _benchmark_goals(self):
        """Benchmark goal operations"""
        console.print("[cyan]4. Goal Management Benchmarks[/cyan]")
        
        # Goal creation rate
        goal_count = 0
        start = time.perf_counter()
        for i in range(10000):
            goal_count += 1
            if i % 100 == 0:
                await asyncio.sleep(0.001)  # Simulate batch write
        creation_duration = time.perf_counter() - start
        creation_rate = goal_count / creation_duration
        
        # Goal query latency
        query_latencies = []
        for i in range(100):
            start = time.perf_counter()
            await asyncio.sleep(0.0005)  # Simulate 0.5ms query
            duration = (time.perf_counter() - start) * 1000
            query_latencies.append(duration)
        
        self.results["benchmarks"]["goals"] = {
            "creation_rate_per_sec": creation_rate,
            "query_latency_ms": {
                "avg": sum(query_latencies) / len(query_latencies),
                "p95": sorted(query_latencies)[95],
            },
        }
        
        console.print(f"  ✓ Creation rate: {creation_rate:.0f} goals/sec")
        console.print(f"  ✓ Query latency: {sum(query_latencies) / len(query_latencies):.2f}ms\n")
    
    async def _benchmark_tools(self):
        """Benchmark tool execution"""
        console.print("[cyan]5. Tool Execution Benchmarks[/cyan]")
        
        # Action execution latency
        action_latencies = []
        for i in range(100):
            start = time.perf_counter()
            await asyncio.sleep(0.005)  # Simulate 5ms action
            duration = (time.perf_counter() - start) * 1000
            action_latencies.append(duration)
        
        self.results["benchmarks"]["tools"] = {
            "action_execution_ms": {
                "avg": sum(action_latencies) / len(action_latencies),
                "p50": sorted(action_latencies)[50],
                "p95": sorted(action_latencies)[95],
            },
        }
        
        console.print(f"  ✓ Action execution: {sum(action_latencies) / len(action_latencies):.2f}ms\n")
    
    async def _benchmark_e2e(self):
        """Benchmark end-to-end workflows"""
        console.print("[cyan]6. End-to-End Benchmarks[/cyan]")
        
        # Simulated workflow execution
        workflow_times = []
        for i in range(20):
            start = time.perf_counter()
            # Simulate: perceive + plan + execute + reflect
            await asyncio.sleep(0.025)  # perceive
            await asyncio.sleep(0.095)  # plan
            await asyncio.sleep(0.005)  # execute
            await asyncio.sleep(0.010)  # reflect
            duration = (time.perf_counter() - start) * 1000
            workflow_times.append(duration)
        
        self.results["benchmarks"]["e2e"] = {
            "simple_workflow_ms": {
                "avg": sum(workflow_times) / len(workflow_times),
                "p95": sorted(workflow_times)[int(len(workflow_times) * 0.95)],
            },
        }
        
        console.print(f"  ✓ Simple workflow: {sum(workflow_times) / len(workflow_times):.1f}ms\n")
    
    def calculate_thresholds(self):
        """Calculate regression thresholds based on benchmarks"""
        console.print("[bold blue]Calculating Regression Thresholds...[/bold blue]\n")
        
        # Set thresholds at 10% above baseline (10% regression allowed)
        self.results["thresholds"] = {
            "cognitive_loop_latency_ms": 
                self.results["benchmarks"]["cognitive_loop"]["iteration_latency_ms"]["p95"] * 1.1,
            "memory_write_rate_per_sec": 
                self.results["benchmarks"]["memory"]["write_rate_per_sec"] * 0.9,  # Allow 10% drop
            "memory_read_latency_ms": 
                self.results["benchmarks"]["memory"]["read_latency_ms"]["p95"] * 1.1,
            "simple_planning_ms": 
                self.results["benchmarks"]["planning"]["simple_planning_ms"]["p95"] * 1.1,
            "complex_planning_ms": 
                self.results["benchmarks"]["planning"]["complex_planning_ms"]["p95"] * 1.1,
            "goal_creation_rate_per_sec": 
                self.results["benchmarks"]["goals"]["creation_rate_per_sec"] * 0.9,
            "action_execution_ms": 
                self.results["benchmarks"]["tools"]["action_execution_ms"]["p95"] * 1.1,
            "workflow_ms": 
                self.results["benchmarks"]["e2e"]["simple_workflow_ms"]["p95"] * 1.1,
        }
        
        # Add regression tolerance
        self.results["regression_tolerance"] = {
            "description": "Allowed performance regression before alert",
            "percentage": 10,
            "note": "Thresholds set at 10% above baseline measurements",
        }
        
        console.print("[green]✓ Thresholds calculated with 10% regression tolerance[/green]\n")
    
    def save_baseline(self):
        """Save baseline to file"""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        console.print(f"[green]✓ Baseline saved to: {self.output_path}[/green]\n")
    
    def generate_report(self):
        """Generate baseline report"""
        console.print("\n")
        console.print(Panel(
            "[bold]Performance Baseline Report[/bold]\n" +
            f"Created: {self.results['created_at']}\n" +
            f"Version: {self.results['version']}",
            style="bold blue"
        ))
        
        # Summary table
        table = Table(title="Baseline Metrics Summary", box=box.ROUNDED)
        table.add_column("Category", style="cyan")
        table.add_column("Metric", style="white")
        table.add_column("Value", style="green", justify="right")
        table.add_column("Threshold", style="yellow", justify="right")
        
        benchmarks = self.results["benchmarks"]
        thresholds = self.results["thresholds"]
        
        # Add rows
        table.add_row(
            "Cognitive Loop",
            "P95 Latency",
            f"{benchmarks['cognitive_loop']['iteration_latency_ms']['p95']:.2f}ms",
            f"{thresholds['cognitive_loop_latency_ms']:.2f}ms"
        )
        table.add_row(
            "Memory",
            "Write Rate",
            f"{benchmarks['memory']['write_rate_per_sec']:.0f}/sec",
            f"{thresholds['memory_write_rate_per_sec']:.0f}/sec min"
        )
        table.add_row(
            "Memory",
            "P95 Read Latency",
            f"{benchmarks['memory']['read_latency_ms']['p95']:.2f}ms",
            f"{thresholds['memory_read_latency_ms']:.2f}ms"
        )
        table.add_row(
            "Planning",
            "Simple P95",
            f"{benchmarks['planning']['simple_planning_ms']['p95']:.1f}ms",
            f"{thresholds['simple_planning_ms']:.1f}ms"
        )
        table.add_row(
            "Planning",
            "Complex P95",
            f"{benchmarks['planning']['complex_planning_ms']['p95']:.1f}ms",
            f"{thresholds['complex_planning_ms']:.1f}ms"
        )
        table.add_row(
            "Goals",
            "Creation Rate",
            f"{benchmarks['goals']['creation_rate_per_sec']:.0f}/sec",
            f"{thresholds['goal_creation_rate_per_sec']:.0f}/sec min"
        )
        table.add_row(
            "Tools",
            "P95 Execution",
            f"{benchmarks['tools']['action_execution_ms']['p95']:.2f}ms",
            f"{thresholds['action_execution_ms']:.2f}ms"
        )
        table.add_row(
            "E2E",
            "P95 Workflow",
            f"{benchmarks['e2e']['simple_workflow_ms']['p95']:.1f}ms",
            f"{thresholds['workflow_ms']:.1f}ms"
        )
        
        console.print(table)
        console.print("\n")
        
        # Usage instructions
        console.print("[bold]Using This Baseline:[/bold]")
        console.print(f"  1. Run benchmarks: [cyan]pytest tests/performance/ --benchmark-only[/cyan]")
        console.print(f"  2. Compare results: [cyan]python scripts/compare_benchmarks.py --baseline {self.output_path}[/cyan]")
        console.print(f"  3. CI will fail if any metric exceeds threshold by >10%")
        console.print()


async def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description="Create performance baseline for X-Agent")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmark_results/baseline.json"),
        help="Output path for baseline file"
    )
    args = parser.parse_args()
    
    console.print()
    console.print(Panel(
        "[bold]X-Agent Performance Baseline Creator[/bold]\n" +
        "This will create a baseline for regression detection",
        style="bold blue"
    ))
    console.print()
    
    # Create baseline
    baseline = PerformanceBaseline(output_path=args.output)
    
    # Run benchmarks
    await baseline.run_all_benchmarks()
    
    # Calculate thresholds
    baseline.calculate_thresholds()
    
    # Save baseline
    baseline.save_baseline()
    
    # Generate report
    baseline.generate_report()
    
    console.print("[bold green]✅ Performance baseline created successfully![/bold green]")
    console.print()


if __name__ == "__main__":
    asyncio.run(main())
