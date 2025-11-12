"""Command-line interface for X-Agent using Typer."""

import asyncio
from typing import Annotated

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from xagent.core.agent import XAgent
from xagent.core.goal_engine import GoalMode
from xagent.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)

# Create Typer app
app = typer.Typer(
    name="xagent",
    help="X-Agent - Autonomous AI Agent CLI",
    add_completion=True,
)

# Rich console for beautiful output
console = Console()

# Global agent instance for interactive mode
_agent: XAgent | None = None


def get_agent() -> XAgent:
    """Get or initialize the global agent instance."""
    global _agent
    if _agent is None:
        raise typer.BadParameter("Agent not initialized. Run 'xagent interactive' first.")
    return _agent


async def initialize_agent() -> XAgent:
    """Initialize and return a new agent instance."""
    global _agent

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Initializing agent...", total=None)

        configure_logging()
        _agent = XAgent()
        await _agent.initialize()

        progress.update(task, completed=True)

    console.print("[green]✓[/green] Agent initialized successfully!", style="bold green")
    return _agent


@app.command()
def interactive() -> None:
    """
    Start X-Agent in interactive mode.

    This launches an interactive shell where you can control the agent
    with commands like start, stop, status, goal, etc.
    """
    console.print(
        Panel.fit(
            "[bold cyan]X-Agent[/bold cyan] - Autonomous AI Agent\n"
            "[dim]Type 'help' for available commands[/dim]",
            border_style="cyan",
            box=box.DOUBLE,
        )
    )

    # Initialize agent
    asyncio.run(initialize_agent())

    # Start interactive loop
    asyncio.run(_interactive_loop())


async def _interactive_loop() -> None:
    """Main interactive command loop."""
    running = True

    while running:
        try:
            # Get user input
            command = console.input("\n[bold cyan]X-Agent>[/bold cyan] ")
            command = command.strip()

            if not command:
                continue

            # Parse command
            parts = command.split(maxsplit=1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

            if cmd == "help":
                _print_interactive_help()
            elif cmd == "start":
                await _cmd_start(args)
            elif cmd == "stop":
                await _cmd_stop()
            elif cmd == "status":
                await _cmd_status()
            elif cmd == "goal":
                await _cmd_goal(args)
            elif cmd == "goals":
                await _cmd_list_goals()
            elif cmd == "command":
                await _cmd_send_command(args)
            elif cmd == "feedback":
                await _cmd_send_feedback(args)
            elif cmd in ["exit", "quit"]:
                running = False
            else:
                console.print(f"[red]Unknown command:[/red] {cmd}", style="bold")
                console.print("Type 'help' for available commands")

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Received interrupt signal[/yellow]")
            break
        except Exception as e:
            logger.error(f"Error in command loop: {e}", exc_info=True)
            console.print(f"[red]Error:[/red] {e}", style="bold red")

    # Cleanup
    if _agent:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Cleaning up...", total=None)
            await _agent.stop()
            progress.update(task, completed=True)

        console.print("[green]✓[/green] Cleanup complete", style="bold green")


def _print_interactive_help() -> None:
    """Print help message for interactive mode."""
    table = Table(
        title="Available Commands", box=box.ROUNDED, show_header=True, header_style="bold cyan"
    )
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")

    table.add_row("start [goal]", "Start the agent with optional initial goal")
    table.add_row("stop", "Stop the agent")
    table.add_row("status", "Show agent status")
    table.add_row("goal <description>", "Create a new goal")
    table.add_row("goals", "List all goals")
    table.add_row("command <text>", "Send a command to the agent")
    table.add_row("feedback <text>", "Send feedback to the agent")
    table.add_row("help", "Show this help message")
    table.add_row("exit/quit", "Exit the CLI")

    console.print(table)


async def _cmd_start(goal: str) -> None:
    """Start the agent."""
    agent = get_agent()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Starting agent...", total=None)
        initial_goal = goal if goal else None
        await agent.start(initial_goal=initial_goal)
        progress.update(task, completed=True)

    console.print("[green]✓[/green] Agent started!", style="bold green")


async def _cmd_stop() -> None:
    """Stop the agent."""
    agent = get_agent()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Stopping agent...", total=None)
        await agent.stop()
        progress.update(task, completed=True)

    console.print("[green]✓[/green] Agent stopped!", style="bold green")


async def _cmd_status() -> None:
    """Show agent status."""
    agent = get_agent()
    status = await agent.get_status()

    # Create status panel
    status_info = f"""[bold]Initialized:[/bold] {'✓' if status['initialized'] else '✗'}
[bold]Running:[/bold] {'✓' if status['running'] else '✗'}
[bold]State:[/bold] {status['state']}
[bold]Iterations:[/bold] {status['iteration_count']}"""

    console.print(
        Panel(status_info, title="[bold cyan]Agent Status[/bold cyan]", border_style="cyan")
    )

    # Goals summary table
    goals_table = Table(
        title="Goals Summary", box=box.SIMPLE, show_header=True, header_style="bold"
    )
    goals_table.add_column("Metric", style="cyan")
    goals_table.add_column("Count", style="white", justify="right")

    goals_table.add_row("Total", str(status["goals_summary"]["total"]))
    goals_table.add_row("Pending", str(status["goals_summary"]["pending"]))
    goals_table.add_row("In Progress", str(status["goals_summary"]["in_progress"]))
    goals_table.add_row("Completed", str(status["goals_summary"]["completed"]))

    console.print(goals_table)

    # Active goal
    if status.get("active_goal"):
        goal = status["active_goal"]
        goal_info = f"""[bold]ID:[/bold] {goal['id']}
[bold]Description:[/bold] {goal['description']}
[bold]Status:[/bold] {goal['status']}
[bold]Mode:[/bold] {goal['mode']}"""
        console.print(
            Panel(goal_info, title="[bold cyan]Active Goal[/bold cyan]", border_style="cyan")
        )

    # Performance
    perf = status["performance"]
    perf_table = Table(title="Performance", box=box.SIMPLE, show_header=True, header_style="bold")
    perf_table.add_column("Metric", style="cyan")
    perf_table.add_column("Value", style="white", justify="right")

    perf_table.add_row("Total Actions", str(perf["total_actions"]))
    perf_table.add_row("Success Rate", f"{perf['success_rate']:.2%}")

    console.print(perf_table)


async def _cmd_goal(description: str) -> None:
    """Create a new goal."""
    agent = get_agent()

    if not description:
        console.print("[red]Error:[/red] Please provide a goal description", style="bold red")
        return

    goal = agent.goal_engine.create_goal(
        description=description,
        mode=GoalMode.GOAL_ORIENTED,
        priority=5,
    )

    console.print(f"[green]✓[/green] Created goal: [cyan]{goal.id}[/cyan]", style="bold")
    console.print(f"Description: {goal.description}")


async def _cmd_list_goals() -> None:
    """List all goals."""
    agent = get_agent()
    goals = agent.goal_engine.list_goals()

    if not goals:
        console.print("[yellow]No goals found[/yellow]")
        return

    table = Table(
        title=f"Goals ({len(goals)} total)",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")
    table.add_column("Status", style="yellow")
    table.add_column("Mode", style="magenta")
    table.add_column("Priority", style="green", justify="right")

    for goal in goals:
        table.add_row(
            goal.id,
            goal.description[:50] + "..." if len(goal.description) > 50 else goal.description,
            goal.status.value,
            goal.mode.value,
            str(goal.priority),
        )

    console.print(table)


async def _cmd_send_command(command: str) -> None:
    """Send a command to the agent."""
    agent = get_agent()

    if not command:
        console.print("[red]Error:[/red] Please provide a command", style="bold red")
        return

    await agent.send_command(command)
    console.print("[green]✓[/green] Command sent!", style="bold green")


async def _cmd_send_feedback(feedback: str) -> None:
    """Send feedback to the agent."""
    agent = get_agent()

    if not feedback:
        console.print("[red]Error:[/red] Please provide feedback", style="bold red")
        return

    await agent.send_feedback(feedback)
    console.print("[green]✓[/green] Feedback sent!", style="bold green")


@app.command()
def start(
    goal: Annotated[str | None, typer.Argument(help="Initial goal for the agent")] = None,
    background: Annotated[
        bool, typer.Option("--background", "-b", help="Run in background mode")
    ] = False,
) -> None:
    """
    Start the X-Agent with an optional initial goal.

    Examples:
        xagent start "Write a Python script to analyze CSV data"
        xagent start --background "Monitor system logs"
    """
    console.print(
        Panel.fit(
            "[bold cyan]X-Agent[/bold cyan] - Starting Agent",
            border_style="cyan",
        )
    )

    async def _start() -> None:
        agent = await initialize_agent()
        await agent.start(initial_goal=goal)

        if background:
            console.print("[green]✓[/green] Agent started in background mode", style="bold green")
        else:
            console.print("[green]✓[/green] Agent started!", style="bold green")
            console.print("[dim]Use 'xagent status' to check agent status[/dim]")

    asyncio.run(_start())


@app.command()
def status() -> None:
    """
    Show the current status of the X-Agent.

    Displays information about agent state, goals, and performance.
    """

    async def _show_status() -> None:
        # For now, show message that agent needs to be initialized
        console.print(
            "[yellow]Note:[/yellow] Agent must be running to show status", style="bold yellow"
        )
        console.print("[dim]Run 'xagent interactive' to start the agent[/dim]")

    asyncio.run(_show_status())


@app.command()
def version() -> None:
    """Show X-Agent version information."""
    console.print(
        Panel.fit(
            "[bold cyan]X-Agent[/bold cyan] v0.1.0\n"
            "[dim]Autonomous AI Agent Platform[/dim]\n\n"
            "[bold]Status:[/bold] Alpha - Active Development\n"
            "[bold]Progress:[/bold] ~94% Production Ready",
            border_style="cyan",
            box=box.DOUBLE,
        )
    )


@app.command(name="completion")
def install_completion(
    shell: Annotated[
        str,
        typer.Argument(help="Shell type: bash, zsh, fish, or powershell"),
    ] = "bash",
    install: Annotated[
        bool,
        typer.Option("--install/--show", help="Install completion or just show instructions"),
    ] = False,
) -> None:
    """
    Install or show shell completion instructions.
    
    Supports bash, zsh, fish, and powershell.
    
    Examples:
        # Show bash completion instructions
        xagent completion bash
        
        # Install bash completion
        xagent completion bash --install
        
        # Show zsh completion instructions
        xagent completion zsh
    """
    shell = shell.lower()
    
    if shell not in ["bash", "zsh", "fish", "powershell"]:
        console.print(f"[red]Error:[/red] Unsupported shell: {shell}", style="bold red")
        console.print("Supported shells: bash, zsh, fish, powershell")
        raise typer.Exit(1)
    
    if install:
        # Try to install completion
        import os
        import subprocess
        from pathlib import Path
        
        try:
            if shell == "bash":
                # Install bash completion
                completion_dir = Path.home() / ".bash_completion.d"
                completion_dir.mkdir(exist_ok=True)
                completion_file = completion_dir / "xagent"
                
                # Generate completion script
                result = subprocess.run(
                    ["xagent", "--show-completion", "bash"],
                    capture_output=True,
                    text=True,
                )
                
                if result.returncode == 0:
                    completion_file.write_text(result.stdout)
                    
                    # Add source to .bashrc if not already there
                    bashrc = Path.home() / ".bashrc"
                    bashrc_content = bashrc.read_text() if bashrc.exists() else ""
                    
                    source_line = f"source {completion_file}\n"
                    if source_line not in bashrc_content:
                        with bashrc.open("a") as f:
                            f.write(f"\n# X-Agent shell completion\n{source_line}")
                    
                    console.print(f"[green]✓[/green] Bash completion installed to {completion_file}")
                    console.print("\n[yellow]Run:[/yellow] source ~/.bashrc")
                    console.print("[dim]Or restart your terminal[/dim]")
                else:
                    raise Exception(result.stderr)
                    
            elif shell == "zsh":
                # Install zsh completion
                completion_dir = Path.home() / ".zsh" / "completion"
                completion_dir.mkdir(parents=True, exist_ok=True)
                completion_file = completion_dir / "_xagent"
                
                # Generate completion script
                result = subprocess.run(
                    ["xagent", "--show-completion", "zsh"],
                    capture_output=True,
                    text=True,
                )
                
                if result.returncode == 0:
                    completion_file.write_text(result.stdout)
                    
                    # Add to fpath in .zshrc if not already there
                    zshrc = Path.home() / ".zshrc"
                    zshrc_content = zshrc.read_text() if zshrc.exists() else ""
                    
                    fpath_line = f'fpath=({completion_dir} $fpath)\n'
                    if str(completion_dir) not in zshrc_content:
                        with zshrc.open("a") as f:
                            f.write(f"\n# X-Agent shell completion\n{fpath_line}")
                            f.write("autoload -Uz compinit && compinit\n")
                    
                    console.print(f"[green]✓[/green] Zsh completion installed to {completion_file}")
                    console.print("\n[yellow]Run:[/yellow] source ~/.zshrc")
                    console.print("[dim]Or restart your terminal[/dim]")
                else:
                    raise Exception(result.stderr)
                    
            elif shell == "fish":
                # Install fish completion
                completion_dir = Path.home() / ".config" / "fish" / "completions"
                completion_dir.mkdir(parents=True, exist_ok=True)
                completion_file = completion_dir / "xagent.fish"
                
                # Generate completion script
                result = subprocess.run(
                    ["xagent", "--show-completion", "fish"],
                    capture_output=True,
                    text=True,
                )
                
                if result.returncode == 0:
                    completion_file.write_text(result.stdout)
                    console.print(f"[green]✓[/green] Fish completion installed to {completion_file}")
                    console.print("\n[dim]Fish will automatically load completions[/dim]")
                else:
                    raise Exception(result.stderr)
                    
            elif shell == "powershell":
                console.print("[yellow]PowerShell completion installation:[/yellow]")
                console.print("1. Run: xagent --show-completion powershell > xagent_completion.ps1")
                console.print("2. Add to your PowerShell profile:")
                console.print("   . /path/to/xagent_completion.ps1")
                
        except Exception as e:
            console.print(f"[red]Error installing completion:[/red] {e}", style="bold red")
            console.print("\n[yellow]Try manual installation instead:[/yellow]")
            console.print(f"xagent completion {shell}")
            raise typer.Exit(1)
    else:
        # Show installation instructions
        console.print(
            Panel.fit(
                f"[bold cyan]Shell Completion for {shell.upper()}[/bold cyan]",
                border_style="cyan",
            )
        )
        
        if shell == "bash":
            console.print("\n[bold]Option 1: Automatic Installation[/bold]")
            console.print("  xagent completion bash --install")
            
            console.print("\n[bold]Option 2: Manual Installation[/bold]")
            console.print("  # Generate completion script")
            console.print("  xagent --show-completion bash > ~/.bash_completion.d/xagent")
            console.print("\n  # Add to ~/.bashrc")
            console.print("  echo 'source ~/.bash_completion.d/xagent' >> ~/.bashrc")
            console.print("\n  # Reload")
            console.print("  source ~/.bashrc")
            
        elif shell == "zsh":
            console.print("\n[bold]Option 1: Automatic Installation[/bold]")
            console.print("  xagent completion zsh --install")
            
            console.print("\n[bold]Option 2: Manual Installation[/bold]")
            console.print("  # Create completion directory")
            console.print("  mkdir -p ~/.zsh/completion")
            console.print("\n  # Generate completion script")
            console.print("  xagent --show-completion zsh > ~/.zsh/completion/_xagent")
            console.print("\n  # Add to ~/.zshrc")
            console.print("  echo 'fpath=(~/.zsh/completion $fpath)' >> ~/.zshrc")
            console.print("  echo 'autoload -Uz compinit && compinit' >> ~/.zshrc")
            console.print("\n  # Reload")
            console.print("  source ~/.zshrc")
            
        elif shell == "fish":
            console.print("\n[bold]Option 1: Automatic Installation[/bold]")
            console.print("  xagent completion fish --install")
            
            console.print("\n[bold]Option 2: Manual Installation[/bold]")
            console.print("  # Generate completion script")
            console.print("  xagent --show-completion fish > ~/.config/fish/completions/xagent.fish")
            console.print("\n  # Fish will automatically load completions")
            
        elif shell == "powershell":
            console.print("\n[bold]Manual Installation[/bold]")
            console.print("  # Generate completion script")
            console.print("  xagent --show-completion powershell > xagent_completion.ps1")
            console.print("\n  # Add to your PowerShell profile")
            console.print("  echo '. /path/to/xagent_completion.ps1' >> $PROFILE")
            
        console.print("\n[bold green]After installation:[/bold green]")
        console.print("  Try: xagent [TAB][TAB]")


def main() -> None:
    """Main entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
