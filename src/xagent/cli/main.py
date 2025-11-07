"""Command-line interface for X-Agent."""

import asyncio
import sys
from typing import Optional

from xagent.core.agent import XAgent
from xagent.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


class CLI:
    """Command-line interface for X-Agent."""
    
    def __init__(self) -> None:
        """Initialize CLI."""
        self.agent: Optional[XAgent] = None
        self.running = False
        
    async def start(self) -> None:
        """Start CLI."""
        configure_logging()
        
        print("=" * 60)
        print("X-Agent - Autonomous AI Agent")
        print("=" * 60)
        print()
        
        # Initialize agent
        print("Initializing agent...")
        self.agent = XAgent()
        await self.agent.initialize()
        print("Agent initialized successfully!")
        print()
        
        # Show help
        self.print_help()
        
        # Start command loop
        self.running = True
        await self.command_loop()
        
    async def command_loop(self) -> None:
        """Main command loop."""
        while self.running:
            try:
                # Get user input
                command = await asyncio.get_event_loop().run_in_executor(
                    None, input, "\nX-Agent> "
                )
                
                command = command.strip()
                
                if not command:
                    continue
                    
                # Parse and execute command
                await self.execute_command(command)
                
            except KeyboardInterrupt:
                print("\n\nReceived interrupt signal")
                break
            except Exception as e:
                logger.error(f"Error in command loop: {e}", exc_info=True)
                print(f"Error: {e}")
        
        # Cleanup
        await self.cleanup()
        
    async def execute_command(self, command: str) -> None:
        """Execute a CLI command."""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd == "help":
            self.print_help()
            
        elif cmd == "start":
            await self.cmd_start(args)
            
        elif cmd == "stop":
            await self.cmd_stop()
            
        elif cmd == "status":
            await self.cmd_status()
            
        elif cmd == "goal":
            await self.cmd_goal(args)
            
        elif cmd == "goals":
            await self.cmd_list_goals()
            
        elif cmd == "command":
            await self.cmd_send_command(args)
            
        elif cmd == "feedback":
            await self.cmd_send_feedback(args)
            
        elif cmd == "exit" or cmd == "quit":
            self.running = False
            
        else:
            print(f"Unknown command: {cmd}")
            print("Type 'help' for available commands")
            
    def print_help(self) -> None:
        """Print help message."""
        print("Available commands:")
        print("  start [goal]      - Start the agent with optional initial goal")
        print("  stop              - Stop the agent")
        print("  status            - Show agent status")
        print("  goal <description> - Create a new goal")
        print("  goals             - List all goals")
        print("  command <text>    - Send a command to the agent")
        print("  feedback <text>   - Send feedback to the agent")
        print("  help              - Show this help message")
        print("  exit/quit         - Exit the CLI")
        print()
        
    async def cmd_start(self, goal: str) -> None:
        """Start the agent."""
        if not self.agent:
            print("Agent not initialized")
            return
            
        print("Starting agent...")
        initial_goal = goal if goal else None
        await self.agent.start(initial_goal=initial_goal)
        print("Agent started!")
        
    async def cmd_stop(self) -> None:
        """Stop the agent."""
        if not self.agent:
            print("Agent not initialized")
            return
            
        print("Stopping agent...")
        await self.agent.stop()
        print("Agent stopped!")
        
    async def cmd_status(self) -> None:
        """Show agent status."""
        if not self.agent:
            print("Agent not initialized")
            return
            
        status = await self.agent.get_status()
        
        print("\n" + "=" * 60)
        print("Agent Status")
        print("=" * 60)
        print(f"Initialized: {status['initialized']}")
        print(f"Running: {status['running']}")
        print(f"State: {status['state']}")
        print(f"Iterations: {status['iteration_count']}")
        print()
        print("Goals Summary:")
        print(f"  Total: {status['goals_summary']['total']}")
        print(f"  Pending: {status['goals_summary']['pending']}")
        print(f"  In Progress: {status['goals_summary']['in_progress']}")
        print(f"  Completed: {status['goals_summary']['completed']}")
        print()
        
        if status.get('active_goal'):
            print("Active Goal:")
            goal = status['active_goal']
            print(f"  ID: {goal['id']}")
            print(f"  Description: {goal['description']}")
            print(f"  Status: {goal['status']}")
            print(f"  Mode: {goal['mode']}")
            print()
        
        print("Performance:")
        perf = status['performance']
        print(f"  Total Actions: {perf['total_actions']}")
        print(f"  Success Rate: {perf['success_rate']:.2%}")
        print("=" * 60)
        
    async def cmd_goal(self, description: str) -> None:
        """Create a new goal."""
        if not self.agent:
            print("Agent not initialized")
            return
            
        if not description:
            print("Please provide a goal description")
            return
            
        from xagent.core.goal_engine import GoalMode
        
        goal = self.agent.goal_engine.create_goal(
            description=description,
            mode=GoalMode.GOAL_ORIENTED,
            priority=5,
        )
        
        print(f"Created goal: {goal.id}")
        print(f"Description: {goal.description}")
        
    async def cmd_list_goals(self) -> None:
        """List all goals."""
        if not self.agent:
            print("Agent not initialized")
            return
            
        goals = self.agent.goal_engine.list_goals()
        
        if not goals:
            print("No goals found")
            return
            
        print("\n" + "=" * 60)
        print(f"Goals ({len(goals)} total)")
        print("=" * 60)
        
        for goal in goals:
            print(f"\nID: {goal.id}")
            print(f"Description: {goal.description}")
            print(f"Status: {goal.status.value}")
            print(f"Mode: {goal.mode.value}")
            print(f"Priority: {goal.priority}")
            
        print("=" * 60)
        
    async def cmd_send_command(self, command: str) -> None:
        """Send a command to the agent."""
        if not self.agent:
            print("Agent not initialized")
            return
            
        if not command:
            print("Please provide a command")
            return
            
        await self.agent.send_command(command)
        print("Command sent!")
        
    async def cmd_send_feedback(self, feedback: str) -> None:
        """Send feedback to the agent."""
        if not self.agent:
            print("Agent not initialized")
            return
            
        if not feedback:
            print("Please provide feedback")
            return
            
        await self.agent.send_feedback(feedback)
        print("Feedback sent!")
        
    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self.agent:
            print("\nCleaning up...")
            await self.agent.stop()
            print("Cleanup complete")


async def main() -> None:
    """Main entry point for CLI."""
    cli = CLI()
    await cli.start()


if __name__ == "__main__":
    asyncio.run(main())
