#!/usr/bin/env python3
"""
Benchmark Comparison Script
============================

Compares current benchmark results against a baseline to detect performance regressions.

Usage:
    python scripts/compare_benchmarks.py --baseline baseline.json --current results.json
    
Exit codes:
    0 - No regressions detected
    1 - Regressions detected (>10% slower than threshold)
    2 - Error reading files
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()


class BenchmarkComparison:
    """Compares benchmark results against baseline"""
    
    def __init__(self, baseline_path: Path, current_path: Path):
        self.baseline_path = baseline_path
        self.current_path = current_path
        self.baseline = None
        self.current = None
        self.regressions = []
        self.improvements = []
        self.stable = []
    
    def load_data(self) -> bool:
        """Load baseline and current results"""
        try:
            with open(self.baseline_path) as f:
                self.baseline = json.load(f)
            console.print(f"[green]✓ Loaded baseline from {self.baseline_path}[/green]")
        except FileNotFoundError:
            console.print(f"[red]✗ Baseline file not found: {self.baseline_path}[/red]")
            return False
        except json.JSONDecodeError as e:
            console.print(f"[red]✗ Invalid JSON in baseline: {e}[/red]")
            return False
        
        try:
            with open(self.current_path) as f:
                self.current = json.load(f)
            console.print(f"[green]✓ Loaded current results from {self.current_path}[/green]")
        except FileNotFoundError:
            console.print(f"[red]✗ Current results file not found: {self.current_path}[/red]")
            return False
        except json.JSONDecodeError as e:
            console.print(f"[red]✗ Invalid JSON in current results: {e}[/red]")
            return False
        
        return True
    
    def compare_metrics(self):
        """Compare all metrics"""
        console.print("\n[bold blue]Comparing Metrics...[/bold blue]\n")
        
        thresholds = self.baseline.get("thresholds", {})
        current_benchmarks = self.current.get("benchmarks", {})
        
        # Define comparisons (metric_name, threshold_key, current_path, higher_is_better)
        comparisons = [
            ("Cognitive Loop P95 Latency", "cognitive_loop_latency_ms",
             ["cognitive_loop", "iteration_latency_ms", "p95"], False),
            
            ("Memory Write Rate", "memory_write_rate_per_sec",
             ["memory", "write_rate_per_sec"], True),
            
            ("Memory Read P95 Latency", "memory_read_latency_ms",
             ["memory", "read_latency_ms", "p95"], False),
            
            ("Simple Planning P95", "simple_planning_ms",
             ["planning", "simple_planning_ms", "p95"], False),
            
            ("Complex Planning P95", "complex_planning_ms",
             ["planning", "complex_planning_ms", "p95"], False),
            
            ("Goal Creation Rate", "goal_creation_rate_per_sec",
             ["goals", "creation_rate_per_sec"], True),
            
            ("Action Execution P95", "action_execution_ms",
             ["tools", "action_execution_ms", "p95"], False),
            
            ("E2E Workflow P95", "workflow_ms",
             ["e2e", "simple_workflow_ms", "p95"], False),
        ]
        
        for name, threshold_key, path, higher_is_better in comparisons:
            threshold = thresholds.get(threshold_key)
            
            # Navigate to current value
            current_value = current_benchmarks
            try:
                for key in path:
                    current_value = current_value[key]
            except (KeyError, TypeError):
                console.print(f"[yellow]⚠ {name}: Not found in current results[/yellow]")
                continue
            
            if threshold is None:
                console.print(f"[yellow]⚠ {name}: No threshold defined[/yellow]")
                continue
            
            # Calculate difference
            if higher_is_better:
                # For metrics where higher is better (throughput, rate)
                pct_diff = ((current_value - threshold) / threshold) * 100
                is_regression = current_value < threshold
            else:
                # For metrics where lower is better (latency, duration)
                pct_diff = ((current_value - threshold) / threshold) * 100
                is_regression = current_value > threshold
            
            # Categorize result
            result = {
                "name": name,
                "current": current_value,
                "threshold": threshold,
                "pct_diff": pct_diff,
                "is_regression": is_regression,
            }
            
            if is_regression:
                self.regressions.append(result)
            elif abs(pct_diff) > 5:  # More than 5% improvement
                self.improvements.append(result)
            else:
                self.stable.append(result)
    
    def generate_report(self) -> int:
        """Generate comparison report and return exit code"""
        console.print("\n")
        console.print(Panel(
            "[bold]Benchmark Comparison Report[/bold]",
            style="bold blue"
        ))
        
        # Summary statistics
        total = len(self.regressions) + len(self.improvements) + len(self.stable)
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Total Metrics: {total}")
        console.print(f"  [red]Regressions: {len(self.regressions)}[/red]")
        console.print(f"  [green]Improvements: {len(self.improvements)}[/green]")
        console.print(f"  [dim]Stable: {len(self.stable)}[/dim]")
        console.print()
        
        # Detailed table
        table = Table(title="Detailed Comparison", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Current", style="white", justify="right")
        table.add_column("Threshold", style="yellow", justify="right")
        table.add_column("Change", style="white", justify="right")
        table.add_column("Status", style="bold")
        
        # Add regressions (sorted by severity)
        for result in sorted(self.regressions, key=lambda x: abs(x["pct_diff"]), reverse=True):
            table.add_row(
                result["name"],
                self._format_value(result["current"], result["name"]),
                self._format_value(result["threshold"], result["name"]),
                f"{result['pct_diff']:+.1f}%",
                "[red]REGRESSION[/red]"
            )
        
        # Add improvements
        for result in sorted(self.improvements, key=lambda x: abs(x["pct_diff"]), reverse=True):
            table.add_row(
                result["name"],
                self._format_value(result["current"], result["name"]),
                self._format_value(result["threshold"], result["name"]),
                f"{result['pct_diff']:+.1f}%",
                "[green]IMPROVED[/green]"
            )
        
        # Add stable
        for result in self.stable:
            table.add_row(
                result["name"],
                self._format_value(result["current"], result["name"]),
                self._format_value(result["threshold"], result["name"]),
                f"{result['pct_diff']:+.1f}%",
                "[dim]STABLE[/dim]"
            )
        
        console.print(table)
        console.print()
        
        # Regression details
        if self.regressions:
            console.print("[bold red]⚠️ PERFORMANCE REGRESSIONS DETECTED[/bold red]\n")
            
            for result in self.regressions:
                console.print(f"  • [red]{result['name']}[/red]")
                console.print(f"    Current: {self._format_value(result['current'], result['name'])}")
                console.print(f"    Threshold: {self._format_value(result['threshold'], result['name'])}")
                console.print(f"    Regression: {abs(result['pct_diff']):.1f}% slower\n")
            
            console.print("[bold]Action Required:[/bold]")
            console.print("  1. Investigate the regression")
            console.print("  2. Optimize the code or update baseline if intentional")
            console.print("  3. Re-run benchmarks to verify fix")
            console.print()
            
            return 1  # Exit with error code
        
        elif self.improvements:
            console.print("[bold green]✅ Performance Improved![/bold green]\n")
            
            for result in self.improvements:
                console.print(f"  • [green]{result['name']}[/green]")
                console.print(f"    Improvement: {abs(result['pct_diff']):.1f}% better\n")
            
            console.print("[bold]Consider:[/bold]")
            console.print("  • Updating baseline to reflect improvements")
            console.print("  • Documenting optimization techniques")
            console.print()
        
        else:
            console.print("[bold green]✅ All Metrics Stable[/bold green]\n")
            console.print("  No significant performance changes detected")
            console.print()
        
        return 0  # Success
    
    def _format_value(self, value: float, metric_name: str) -> str:
        """Format value based on metric type"""
        if "rate" in metric_name.lower() or "Rate" in metric_name:
            return f"{value:.0f}/sec"
        elif "latency" in metric_name.lower() or "Latency" in metric_name:
            return f"{value:.2f}ms"
        elif "ms" in metric_name or "MS" in metric_name:
            return f"{value:.2f}ms"
        else:
            return f"{value:.2f}"


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description="Compare benchmarks against baseline")
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path("benchmark_results/baseline.json"),
        help="Path to baseline file"
    )
    parser.add_argument(
        "--current",
        type=Path,
        default=Path("benchmark_results/current.json"),
        help="Path to current results file"
    )
    args = parser.parse_args()
    
    console.print()
    console.print(Panel(
        "[bold]X-Agent Benchmark Comparison[/bold]\n" +
        "Detecting performance regressions",
        style="bold blue"
    ))
    console.print()
    
    # Create comparison
    comparison = BenchmarkComparison(args.baseline, args.current)
    
    # Load data
    if not comparison.load_data():
        console.print("\n[red]Failed to load benchmark data[/red]")
        return 2
    
    # Compare metrics
    comparison.compare_metrics()
    
    # Generate report and get exit code
    exit_code = comparison.generate_report()
    
    if exit_code == 0:
        console.print("[bold green]✅ No performance regressions detected[/bold green]")
    elif exit_code == 1:
        console.print("[bold red]❌ Performance regressions detected - Build should FAIL[/bold red]")
    
    console.print()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
