#!/usr/bin/env python3
"""
Central Test Coverage Control Point for X-Agent

This script provides centralized control over test execution and coverage reporting.
It enforces the 90% coverage requirement and provides detailed reporting.

Usage:
    python scripts/run_tests.py              # Run all tests with coverage
    python scripts/run_tests.py --unit       # Run only unit tests
    python scripts/run_tests.py --report     # Generate HTML coverage report
    python scripts/run_tests.py --strict     # Enforce 90% coverage requirement
"""

import sys
import subprocess
import argparse
from pathlib import Path


# Coverage thresholds
COVERAGE_THRESHOLD = 90.0

# Modules that require integration testing (excluded from unit test coverage)
INTEGRATION_MODULES = [
    "xagent.api.rest",
    "xagent.api.websocket",
    "xagent.cli.main",
    "xagent.core.agent",
    "xagent.core.cognitive_loop",
    "xagent.memory.memory_layer",
    "xagent.security.policy",
    "xagent.tools.tool_server",
]

# Core modules that should have unit test coverage
CORE_MODULES = [
    "xagent.config",
    "xagent.core.goal_engine",
    "xagent.core.planner",
    "xagent.core.executor",
    "xagent.core.metacognition",
    "xagent.utils.logging",
]


def run_command(cmd: list, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=check, capture_output=True, text=True)
    if result.returncode != 0 and check:
        print(f"Error: {result.stderr}")
        sys.exit(result.returncode)
    return result


def run_unit_tests(verbose: bool = True) -> None:
    """Run unit tests with coverage."""
    cmd = [
        "python3", "-m", "pytest",
        "tests/unit/",
        "-v" if verbose else "-q",
        "--tb=short",
    ]
    
    env = {"PYTHONPATH": "src"}
    subprocess.run(cmd, env=env, check=True)


def run_coverage(html_report: bool = False, strict: bool = False) -> float:
    """Run coverage analysis and return coverage percentage."""
    # Clean previous coverage data
    run_command(["python3", "-m", "coverage", "erase"], check=False)
    
    # Run tests with coverage
    cmd = [
        "python3", "-m", "coverage", "run",
        "--source=src/xagent",
        "-m", "pytest", "tests/unit/", "-q"
    ]
    
    env = {"PYTHONPATH": "src"}
    subprocess.run(cmd, env=env, check=False)
    
    # Generate report
    result = run_command(
        ["python3", "-m", "coverage", "report", "--precision=2"],
        check=False
    )
    
    # Parse coverage percentage from output
    lines = result.stdout.split("\n")
    for line in lines:
        if "TOTAL" in line:
            parts = line.split()
            for part in parts:
                if "%" in part:
                    coverage_pct = float(part.replace("%", ""))
                    print(f"\n{'=' * 70}")
                    print(f"Total Coverage: {coverage_pct:.2f}%")
                    print(f"Target Coverage: {COVERAGE_THRESHOLD}%")
                    
                    if coverage_pct >= COVERAGE_THRESHOLD:
                        print(f"✅ Coverage requirement MET ({coverage_pct:.2f}% >= {COVERAGE_THRESHOLD}%)")
                    else:
                        print(f"❌ Coverage requirement NOT MET ({coverage_pct:.2f}% < {COVERAGE_THRESHOLD}%)")
                        if strict:
                            print(f"{'=' * 70}\n")
                            sys.exit(1)
                    
                    print(f"{'=' * 70}\n")
                    
                    if html_report:
                        run_command(["python3", "-m", "coverage", "html"])
                        print("HTML coverage report generated in: htmlcov/index.html")
                    
                    return coverage_pct
    
    return 0.0


def run_core_module_coverage() -> None:
    """Run coverage analysis on core modules only."""
    print("=" * 70)
    print("CORE MODULES COVERAGE REPORT")
    print("=" * 70)
    print("\nTesting core unit-testable modules:")
    for module in CORE_MODULES:
        print(f"  - {module}")
    print()
    
    # Run coverage
    run_command(["python3", "-m", "coverage", "erase"], check=False)
    
    cmd = [
        "python3", "-m", "coverage", "run",
        "--source=src/xagent",
        "-m", "pytest", "tests/unit/", "-q"
    ]
    
    subprocess.run(cmd, env={"PYTHONPATH": "src"}, check=False)
    
    # Report on specific modules
    modules_paths = [f"src/{m.replace('.', '/')}.py" for m in CORE_MODULES]
    include_pattern = ",".join(modules_paths)
    
    result = run_command(
        ["python3", "-m", "coverage", "report", 
         "--precision=2",
         f"--include={include_pattern}"],
        check=False
    )
    
    print(result.stdout)
    
    # Calculate total coverage for core modules
    lines = result.stdout.split("\n")
    for line in lines:
        if "TOTAL" in line:
            parts = line.split()
            for i, part in enumerate(parts):
                if "%" in part:
                    coverage_pct = float(part.replace("%", ""))
                    print(f"\n{'=' * 70}")
                    print(f"Core Modules Coverage: {coverage_pct:.2f}%")
                    print(f"Target Coverage: {COVERAGE_THRESHOLD}%")
                    
                    if coverage_pct >= COVERAGE_THRESHOLD:
                        print(f"✅ PASSED: Coverage >= {COVERAGE_THRESHOLD}%")
                    else:
                        print(f"❌ FAILED: Coverage < {COVERAGE_THRESHOLD}%")
                    print(f"{'=' * 70}\n")
                    break


def main():
    parser = argparse.ArgumentParser(
        description="Central Test Coverage Control for X-Agent"
    )
    parser.add_argument(
        "--unit", action="store_true",
        help="Run only unit tests"
    )
    parser.add_argument(
        "--report", action="store_true",
        help="Generate HTML coverage report"
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Enforce 90%% coverage requirement (fail if not met)"
    )
    parser.add_argument(
        "--core", action="store_true",
        help="Show coverage for core modules only"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("X-AGENT TEST COVERAGE CONTROL")
    print("=" * 70)
    print()
    
    if args.core:
        run_core_module_coverage()
    elif args.unit:
        run_unit_tests(verbose=args.verbose)
    else:
        run_coverage(html_report=args.report, strict=args.strict)


if __name__ == "__main__":
    main()
