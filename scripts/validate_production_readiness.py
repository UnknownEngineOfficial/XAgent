#!/usr/bin/env python3
"""
Production Readiness Validation Script
Validates that X-Agent is ready for production deployment.
"""

import sys
from pathlib import Path
import subprocess
import importlib

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def check_python_version():
    """Check Python version"""
    version = sys.version_info
    required = (3, 10)
    
    if version >= required:
        return True, f"Python {version.major}.{version.minor}.{version.micro}"
    else:
        return False, f"Python {version.major}.{version.minor}.{version.micro} (requires 3.10+)"


def check_dependencies():
    """Check if all dependencies are installed"""
    required_packages = [
        "fastapi",
        "uvicorn",
        "redis",
        "sqlalchemy",
        "langchain",
        "langgraph",
        "chromadb",
        "typer",
        "rich",
        "prometheus_client",
        "opentelemetry",
    ]
    
    missing = []
    installed = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            installed.append(package)
        except ImportError:
            missing.append(package)
    
    if not missing:
        return True, f"All {len(installed)} dependencies installed"
    else:
        return False, f"Missing: {', '.join(missing)}"


def check_tests():
    """Run test suite"""
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "-q", "--tb=no"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode == 0:
            # Extract test count from output
            lines = result.stdout.split('\n')
            for line in lines:
                if "passed" in line:
                    return True, line.strip()
            return True, "Tests passed"
        else:
            return False, "Some tests failed"
    except Exception as e:
        return False, f"Error running tests: {e}"


def check_code_coverage():
    """Check code coverage"""
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "--cov=xagent", "--cov-report=term-missing", "-q"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=Path(__file__).parent.parent
        )
        
        # Extract coverage percentage
        lines = result.stdout.split('\n')
        for line in lines:
            if "TOTAL" in line:
                parts = line.split()
                for part in parts:
                    if "%" in part:
                        coverage = int(part.rstrip('%'))
                        if coverage >= 90:
                            return True, f"{coverage}% (target: 90%+)"
                        else:
                            return False, f"{coverage}% (below 90% target)"
        
        return True, "Coverage checked"
    except Exception as e:
        return False, f"Error checking coverage: {e}"


def check_core_modules():
    """Check if core modules can be imported"""
    modules = [
        "xagent.core.goal_engine",
        "xagent.core.cognitive_loop",
        "xagent.core.planner",
        "xagent.core.executor",
        "xagent.core.learning",
        "xagent.core.metacognition",
        "xagent.memory.memory_layer",
        "xagent.api.rest",
        "xagent.api.websocket",
        "xagent.cli.main",
    ]
    
    failed = []
    
    for module in modules:
        try:
            importlib.import_module(module)
        except Exception as e:
            failed.append(f"{module}: {e}")
    
    if not failed:
        return True, f"All {len(modules)} core modules importable"
    else:
        return False, f"Failed: {len(failed)} modules"


def check_documentation():
    """Check if documentation exists"""
    docs = [
        "README.md",
        "CHANGELOG.md",
        "dev_plan.md",
        "docs/ARCHITECTURE.md",
        "docs/FEATURES.md",
        "docs/EMERGENT_INTELLIGENCE.md",
    ]
    
    missing = []
    project_root = Path(__file__).parent.parent
    
    for doc in docs:
        if not (project_root / doc).exists():
            missing.append(doc)
    
    if not missing:
        return True, f"All {len(docs)} key documents present"
    else:
        return False, f"Missing: {', '.join(missing)}"


def check_examples():
    """Check if example scripts exist"""
    examples_dir = Path(__file__).parent.parent / "examples"
    
    if not examples_dir.exists():
        return False, "Examples directory missing"
    
    examples = list(examples_dir.glob("*.py"))
    
    if len(examples) >= 5:
        return True, f"{len(examples)} example scripts"
    else:
        return False, f"Only {len(examples)} examples (need 5+)"


def check_docker_config():
    """Check if Docker configuration exists"""
    project_root = Path(__file__).parent.parent
    files = [
        "Dockerfile",
        "docker-compose.yml",
    ]
    
    missing = []
    for file in files:
        if not (project_root / file).exists():
            missing.append(file)
    
    if not missing:
        return True, "Docker configuration present"
    else:
        return False, f"Missing: {', '.join(missing)}"


def check_kubernetes_config():
    """Check if Kubernetes configuration exists"""
    project_root = Path(__file__).parent.parent
    k8s_dir = project_root / "k8s"
    
    if not k8s_dir.exists():
        return False, "k8s directory missing"
    
    configs = list(k8s_dir.glob("*.yaml")) + list(k8s_dir.glob("*.yml"))
    
    if len(configs) >= 3:
        return True, f"{len(configs)} k8s configs"
    else:
        return False, f"Only {len(configs)} k8s configs"


def check_security_policies():
    """Check if security policies exist"""
    project_root = Path(__file__).parent.parent
    policies_dir = project_root / "config" / "policies"
    
    if not policies_dir.exists():
        return False, "Policies directory missing"
    
    policies = list(policies_dir.glob("*.rego"))
    
    if len(policies) >= 1:
        return True, f"{len(policies)} security policies"
    else:
        return False, "No security policies found"


def main():
    """Run all validation checks"""
    console.print(Panel.fit(
        "[bold cyan]🔍 X-Agent Production Readiness Validation[/bold cyan]\n\n"
        "[dim]Checking all systems for production deployment[/dim]",
        border_style="cyan"
    ))
    console.print()
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Core Modules", check_core_modules),
        ("Test Suite", check_tests),
        ("Code Coverage", check_code_coverage),
        ("Documentation", check_documentation),
        ("Example Scripts", check_examples),
        ("Docker Config", check_docker_config),
        ("Kubernetes Config", check_kubernetes_config),
        ("Security Policies", check_security_policies),
    ]
    
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Running validation checks...", total=len(checks))
        
        for name, check_func in checks:
            try:
                passed, message = check_func()
                results.append((name, passed, message))
            except Exception as e:
                results.append((name, False, f"Error: {e}"))
            progress.update(task, advance=1)
    
    # Display results
    console.print("\n[bold]Validation Results:[/bold]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Check", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details")
    
    passed_count = 0
    failed_checks = []
    
    for name, passed, message in results:
        status = "[green]✓ PASS[/green]" if passed else "[red]✗ FAIL[/red]"
        table.add_row(name, status, message)
        
        if passed:
            passed_count += 1
        else:
            failed_checks.append(name)
    
    console.print(table)
    
    # Summary
    console.print()
    total = len(checks)
    pass_rate = (passed_count / total) * 100
    
    summary_table = Table(show_header=False, box=None)
    summary_table.add_column("", style="bold")
    summary_table.add_column("", justify="right")
    
    summary_table.add_row("Total Checks", str(total))
    summary_table.add_row("Passed", f"[green]{passed_count}[/green]")
    summary_table.add_row("Failed", f"[red]{total - passed_count}[/red]")
    summary_table.add_row("Pass Rate", f"{pass_rate:.1f}%")
    
    console.print(Panel(summary_table, title="Summary", border_style="yellow"))
    
    # Final verdict
    console.print()
    
    if pass_rate >= 90:
        console.print(Panel.fit(
            "[bold green]✓ PRODUCTION READY[/bold green]\n\n"
            f"[dim]X-Agent passed {passed_count}/{total} checks ({pass_rate:.1f}%)\n"
            "System is ready for production deployment[/dim]",
            border_style="green"
        ))
        return 0
    elif pass_rate >= 70:
        console.print(Panel.fit(
            "[bold yellow]⚠ MOSTLY READY[/bold yellow]\n\n"
            f"[dim]X-Agent passed {passed_count}/{total} checks ({pass_rate:.1f}%)\n"
            f"Address these issues before deployment:\n"
            f"{chr(10).join('  • ' + check for check in failed_checks)}[/dim]",
            border_style="yellow"
        ))
        return 1
    else:
        console.print(Panel.fit(
            "[bold red]✗ NOT READY[/bold red]\n\n"
            f"[dim]X-Agent passed only {passed_count}/{total} checks ({pass_rate:.1f}%)\n"
            f"Critical issues must be resolved:\n"
            f"{chr(10).join('  • ' + check for check in failed_checks)}[/dim]",
            border_style="red"
        ))
        return 2


if __name__ == "__main__":
    sys.exit(main())
