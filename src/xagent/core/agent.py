"""Main X-Agent class - Autonomous AI Agent."""

import asyncio
from typing import Any

from xagent.config import Settings
from xagent.core.cognitive_loop import CognitiveLoop
from xagent.core.executor import Executor
from xagent.core.goal_engine import GoalEngine, GoalMode
from xagent.core.metacognition import MetaCognitionMonitor
from xagent.core.planner import Planner
from xagent.memory.memory_layer import MemoryLayer
from xagent.planning.langgraph_planner import LangGraphPlanner
from xagent.utils.logging import get_logger

logger = get_logger(__name__)


class XAgent:
    """
    X-Agent - Autonomous AI Agent.

    Self-thinking, decision-making agent that works continuously
    until explicitly stopped or goal is achieved.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize X-Agent.

        Args:
            settings: Optional settings instance. If not provided, loads from environment.
        """
        logger.info("Initializing X-Agent...")

        # Load settings
        self.settings = settings or Settings()

        # Initialize core components
        self.goal_engine = GoalEngine()
        self.memory = MemoryLayer()

        # Choose planner based on configuration
        if self.settings.use_langgraph_planner:
            logger.info("Using LangGraph planner")
            self.planner = LangGraphPlanner()
        else:
            logger.info("Using legacy planner")
            self.planner = Planner()

        self.executor = Executor()
        self.metacognition = MetaCognitionMonitor()

        # Cognitive loop will be initialized after memory
        self.cognitive_loop: CognitiveLoop | None = None

        self.initialized = False

    async def initialize(self) -> None:
        """Initialize all components."""
        if self.initialized:
            logger.warning("X-Agent already initialized")
            return

        # Initialize memory layer
        await self.memory.initialize()

        # Initialize cognitive loop
        self.cognitive_loop = CognitiveLoop(
            goal_engine=self.goal_engine,
            memory=self.memory,
            planner=self.planner,
            executor=self.executor,
        )

        self.initialized = True
        logger.info("X-Agent initialized successfully")

    async def start(self, initial_goal: str | None = None) -> None:
        """
        Start X-Agent.

        Args:
            initial_goal: Optional initial goal description
        """
        if not self.initialized:
            await self.initialize()

        logger.info("Starting X-Agent...")

        # Create initial goal if provided
        if initial_goal:
            goal = self.goal_engine.create_goal(
                description=initial_goal,
                mode=GoalMode.GOAL_ORIENTED,
                priority=10,
            )
            self.goal_engine.set_active_goal(goal.id)
            logger.info(f"Created initial goal: {goal.id}")

        # Start cognitive loop
        if self.cognitive_loop:
            await self.cognitive_loop.start()

    async def stop(self) -> None:
        """Stop X-Agent."""
        logger.info("Stopping X-Agent...")

        if self.cognitive_loop:
            await self.cognitive_loop.stop()

        # Close memory connections
        await self.memory.close()

        logger.info("X-Agent stopped")

    async def send_command(self, command: str) -> None:
        """
        Send a command to the agent.

        Args:
            command: Command text
        """
        if not self.cognitive_loop:
            logger.error("Cognitive loop not initialized")
            return

        await self.cognitive_loop.add_perception(
            {
                "type": "command",
                "content": command,
                "timestamp": asyncio.get_event_loop().time(),
            }
        )

        logger.info(f"Command sent: {command}")

    async def send_feedback(self, feedback: str) -> None:
        """
        Send feedback to the agent.

        Args:
            feedback: Feedback text
        """
        if not self.cognitive_loop:
            logger.error("Cognitive loop not initialized")
            return

        await self.cognitive_loop.add_perception(
            {
                "type": "feedback",
                "content": feedback,
                "timestamp": asyncio.get_event_loop().time(),
            }
        )

        logger.info(f"Feedback sent: {feedback}")

    async def get_status(self) -> dict[str, Any]:
        """
        Get current agent status.

        Returns:
            Status information
        """
        status = {
            "initialized": self.initialized,
            "running": self.cognitive_loop.running if self.cognitive_loop else False,
            "state": self.cognitive_loop.state.value if self.cognitive_loop else "unknown",
            "iteration_count": self.cognitive_loop.iteration_count if self.cognitive_loop else 0,
            "planner_type": "langgraph" if self.settings.use_langgraph_planner else "legacy",
            "active_goal": None,
            "goals_summary": {
                "total": len(self.goal_engine.goals),
                "pending": len(self.goal_engine.list_goals(status="pending")),
                "in_progress": len(self.goal_engine.list_goals(status="in_progress")),
                "completed": len(self.goal_engine.list_goals(status="completed")),
            },
            "performance": self.metacognition.get_performance_summary(),
        }

        active_goal = self.goal_engine.get_active_goal()
        if active_goal:
            status["active_goal"] = active_goal.to_dict()

        return status

    async def create_continuous_task(self, description: str) -> str:
        """
        Create a continuous task (never-ending).

        Args:
            description: Task description

        Returns:
            Goal ID
        """
        goal = self.goal_engine.create_goal(
            description=description,
            mode=GoalMode.CONTINUOUS,
            priority=5,
        )

        logger.info(f"Created continuous task: {goal.id}")
        return goal.id


async def main() -> None:
    """Main entry point for X-Agent."""
    # Configure logging
    from xagent.utils.logging import configure_logging

    configure_logging()

    # Create and initialize agent
    agent = XAgent()
    await agent.initialize()

    # Start agent with initial goal
    await agent.start(
        initial_goal="Analyze system capabilities and prepare for autonomous operation"
    )

    # Keep running
    try:
        while True:
            await asyncio.sleep(1)

            # Print status periodically
            status = await agent.get_status()
            if status["iteration_count"] % 10 == 0:
                logger.info(f"Status: {status}")

    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
