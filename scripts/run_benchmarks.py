#!/usr/bin/env python3
"""
Performance Benchmark Runner for X-Agent.

This script runs comprehensive performance benchmarks and generates reports
to track system performance over time.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_benchmarks(
    output_dir: str = "benchmark_results",
    compare: str | None = None,
    save_baseline: bool = False,
) -> int:
    """
    Run performance benchmarks.
    
    Args:
        output_dir: Directory to save results
        compare: Path to baseline JSON to compare against
        save_baseline: Whether to save this run as a new baseline
        
    Returns:
        Exit code (0 for success)
    """
    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamp for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_path / f"benchmark_{timestamp}.json"
    
    print("=" * 80)
    print("X-Agent Performance Benchmark Suite")
    print("=" * 80)
    print(f"Timestamp: {timestamp}")
    print(f"Output: {output_file}")
    print("=" * 80)
    print()
    
    # Build pytest command
    cmd = [
        "pytest",
        "tests/performance/",
        "--benchmark-only",
        "--benchmark-json=" + str(output_file),
        "--benchmark-columns=min,max,mean,stddev,median,ops,rounds,iterations",
        "--benchmark-sort=mean",
        "-v",
    ]
    
    # Add comparison if specified
    if compare:
        cmd.append(f"--benchmark-compare={compare}")
        cmd.append("--benchmark-compare-fail=mean:10%")  # Fail if 10% slower
    
    print("Running benchmarks...")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    # Run benchmarks
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        print()
        print("❌ Benchmarks failed or had errors")
        return result.returncode
    
    print()
    print("=" * 80)
    print("✅ Benchmarks completed successfully")
    print("=" * 80)
    
    # Load and display summary
    try:
        with open(output_file) as f:
            data = json.load(f)
        
        benchmarks = data.get("benchmarks", [])
        
        print()
        print("Performance Summary:")
        print("-" * 80)
        
        # Group by category
        groups = {}
        for bench in benchmarks:
            group = bench.get("group", "unknown")
            if group not in groups:
                groups[group] = []
            groups[group].append(bench)
        
        for group_name, group_benchmarks in sorted(groups.items()):
            print(f"\n{group_name.upper()}:")
            for bench in group_benchmarks:
                name = bench["name"].replace("test_", "")
                stats = bench["stats"]
                mean_ms = stats["mean"] * 1000  # Convert to ms
                ops = stats.get("ops", 0)
                
                print(f"  {name:50s} {mean_ms:8.2f}ms  ({ops:8.1f} ops/sec)")
        
        print()
        print("-" * 80)
        
        # Calculate overall metrics
        total_time = sum(b["stats"]["mean"] for b in benchmarks)
        avg_time = total_time / len(benchmarks) if benchmarks else 0
        
        print(f"Total benchmarks: {len(benchmarks)}")
        print(f"Total time: {total_time:.3f}s")
        print(f"Average time per benchmark: {avg_time * 1000:.2f}ms")
        
    except Exception as e:
        print(f"⚠️  Could not load benchmark results: {e}")
    
    # Save as baseline if requested
    if save_baseline:
        baseline_file = output_path / "baseline.json"
        subprocess.run(["cp", str(output_file), str(baseline_file)])
        print()
        print(f"📊 Saved baseline to: {baseline_file}")
    
    print()
    print(f"📁 Full results saved to: {output_file}")
    print()
    
    return 0


def compare_benchmarks(current_file: str, baseline_file: str) -> None:
    """
    Compare two benchmark results.
    
    Args:
        current_file: Path to current benchmark JSON
        baseline_file: Path to baseline benchmark JSON
    """
    print("=" * 80)
    print("Benchmark Comparison")
    print("=" * 80)
    
    try:
        with open(current_file) as f:
            current = json.load(f)
        with open(baseline_file) as f:
            baseline = json.load(f)
    except Exception as e:
        print(f"❌ Error loading files: {e}")
        return
    
    current_benchmarks = {b["name"]: b for b in current.get("benchmarks", [])}
    baseline_benchmarks = {b["name"]: b for b in baseline.get("benchmarks", [])}
    
    print()
    print(f"Current:  {current_file}")
    print(f"Baseline: {baseline_file}")
    print()
    print("-" * 80)
    
    regressions = []
    improvements = []
    
    for name in sorted(current_benchmarks.keys()):
        if name not in baseline_benchmarks:
            continue
        
        curr = current_benchmarks[name]
        base = baseline_benchmarks[name]
        
        curr_mean = curr["stats"]["mean"]
        base_mean = base["stats"]["mean"]
        
        diff = curr_mean - base_mean
        pct_change = (diff / base_mean) * 100 if base_mean > 0 else 0
        
        status = "=" if abs(pct_change) < 5 else ("⚠️" if pct_change > 10 else "✅")
        
        print(f"{status} {name:50s} {pct_change:+7.1f}%  "
              f"({base_mean * 1000:.2f}ms → {curr_mean * 1000:.2f}ms)")
        
        if pct_change > 10:
            regressions.append((name, pct_change))
        elif pct_change < -10:
            improvements.append((name, pct_change))
    
    print("-" * 80)
    
    if regressions:
        print()
        print("⚠️  Performance Regressions Detected:")
        for name, pct in sorted(regressions, key=lambda x: -x[1]):
            print(f"  - {name}: {pct:+.1f}%")
    
    if improvements:
        print()
        print("✅ Performance Improvements:")
        for name, pct in sorted(improvements, key=lambda x: x[1]):
            print(f"  + {name}: {pct:+.1f}%")
    
    if not regressions and not improvements:
        print()
        print("✅ No significant performance changes detected")
    
    print()


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run X-Agent performance benchmarks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run benchmarks and save results
  python scripts/run_benchmarks.py
  
  # Run and save as baseline
  python scripts/run_benchmarks.py --save-baseline
  
  # Run and compare against baseline
  python scripts/run_benchmarks.py --compare benchmark_results/baseline.json
  
  # Compare two existing results
  python scripts/run_benchmarks.py --compare-only \\
      benchmark_results/benchmark_20251112_120000.json \\
      benchmark_results/baseline.json
        """,
    )
    
    parser.add_argument(
        "--output-dir",
        default="benchmark_results",
        help="Directory to save results (default: benchmark_results)",
    )
    
    parser.add_argument(
        "--compare",
        help="Path to baseline JSON to compare against",
    )
    
    parser.add_argument(
        "--save-baseline",
        action="store_true",
        help="Save this run as the new baseline",
    )
    
    parser.add_argument(
        "--compare-only",
        nargs=2,
        metavar=("CURRENT", "BASELINE"),
        help="Only compare two existing results (don't run benchmarks)",
    )
    
    args = parser.parse_args()
    
    if args.compare_only:
        compare_benchmarks(args.compare_only[0], args.compare_only[1])
        return 0
    
    return run_benchmarks(
        output_dir=args.output_dir,
        compare=args.compare,
        save_baseline=args.save_baseline,
    )


if __name__ == "__main__":
    sys.exit(main())
