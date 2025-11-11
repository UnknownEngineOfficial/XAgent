"""Main X-Agent class - Autonomous AI Agent."""

import asyncio
from typing import Any, Union

from xagent.config import Settings
from xagent.core.agent_roles import AgentCoordinator
from xagent.core.cognitive_loop import CognitiveLoop
from xagent.core.executor import Executor
from xagent.core.goal_engine import GoalEngine, GoalMode, GoalStatus
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
    
    Uses limited internal agents for coordination:
    - Worker Agent: Handles primary execution and actions
    - Planner Agent: Strategic planning and goal decomposition
    - Chat Agent: Manages user communication and interaction
    - Sub-Agents: Temporary workers for subtasks (max 5-7, configurable)
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

        # Initialize agent coordinator for internal multi-agent coordination
        max_sub_agents = getattr(self.settings, 'max_sub_agents', 5)
        self.agent_coordinator = AgentCoordinator(max_sub_agents=max_sub_agents)
        logger.info(f"Initialized agent coordinator with max {max_sub_agents} sub-agents")

        # Initialize core components
        self.goal_engine = GoalEngine()
        self.memory = MemoryLayer()

        # Choose planner based on configuration
        self.planner: Union[Planner, LangGraphPlanner]
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
                "pending": len(self.goal_engine.list_goals(status=GoalStatus.PENDING)),
                "in_progress": len(self.goal_engine.list_goals(status=GoalStatus.IN_PROGRESS)),
                "completed": len(self.goal_engine.list_goals(status=GoalStatus.COMPLETED)),
            },
            "performance": self.metacognition.get_performance_summary(),
            "agents": self.agent_coordinator.get_status(),
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
    
    async def spawn_subtask_agent(self, task_description: str, parent_goal_id: str | None = None) -> str | None:
        """
        Spawn a mini-agent for parallel subtask execution.
        
        Args:
            task_description: Description of the subtask
            parent_goal_id: Optional parent goal ID
            
        Returns:
            Mini-agent ID if spawned successfully, None if limit reached
        """
        # Get parent agent (main worker)
        parent_agent = self.agent_coordinator.get_main_worker()
        
        # Spawn mini-agent
        mini_agent = self.agent_coordinator.spawn_mini_agent(
            task_description=task_description,
            parent_agent_id=parent_agent.id
        )
        
        if not mini_agent:
            logger.warning("Cannot spawn mini-agent: limit reached")
            return None
        
        # Create a goal for the mini-agent
        goal = self.goal_engine.create_goal(
            description=task_description,
            mode=GoalMode.GOAL_ORIENTED,
            priority=5,
            parent_id=parent_goal_id,
            metadata={"agent_id": mini_agent.id, "agent_role": "mini_agent"}
        )
        
        logger.info(f"Spawned mini-agent {mini_agent.id} for subtask: {task_description}")
        return mini_agent.id
    
    async def terminate_subtask_agent(self, agent_id: str) -> bool:
        """
        Terminate a mini-agent after subtask completion.
        
        Args:
            agent_id: ID of the mini-agent
            
        Returns:
            True if terminated successfully, False otherwise
        """
        result = self.agent_coordinator.terminate_mini_agent(agent_id)
        if result:
            logger.info(f"Terminated mini-agent: {agent_id}")
        return result


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
