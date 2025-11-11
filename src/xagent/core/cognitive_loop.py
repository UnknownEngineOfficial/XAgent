"""Cognitive Loop - The continuous thinking process of X-Agent."""

import asyncio
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, cast

from xagent.config import settings
from xagent.core.goal_engine import GoalEngine, GoalStatus
from xagent.memory.memory_layer import MemoryLayer
from xagent.monitoring.metrics import MetricsCollector
from xagent.utils.logging import get_logger

logger = get_logger(__name__)


class LoopPhase(str, Enum):
    """Cognitive loop phases."""

    PERCEPTION = "perception"
    INTERPRETATION = "interpretation"
    PLANNING = "planning"
    EXECUTION = "execution"
    REFLECTION = "reflection"


class CognitiveState(str, Enum):
    """Cognitive states."""

    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    REFLECTING = "reflecting"
    STOPPED = "stopped"


class CognitiveLoop:
    """
    Cognitive Loop - Permanent thinking cycle.

    Implements the continuous cognitive process:
    Perception → Interpretation → Planning → Execution → Reflection → Loop
    """

    def __init__(
        self,
        goal_engine: GoalEngine,
        memory: MemoryLayer,
        planner: Any,
        executor: Any,
    ) -> None:
        """
        Initialize cognitive loop.

        Args:
            goal_engine: Goal engine instance
            memory: Memory layer instance
            planner: Planner instance
            executor: Executor instance
        """
        self.goal_engine = goal_engine
        self.memory = memory
        self.planner = planner
        self.executor = executor

        self.state = CognitiveState.IDLE
        self.current_phase = LoopPhase.PERCEPTION
        self.running = False
        self.iteration_count = 0
        self.max_iterations = settings.max_iterations

        # Perception queue for inputs
        self.perception_queue: asyncio.Queue = asyncio.Queue()

        # Metrics tracking
        self.metrics = MetricsCollector()
        self.start_time: float | None = None
        self.task_results: list[bool] = []  # Track last 100 task results

    async def start(self) -> None:
        """Start the cognitive loop."""
        if self.running:
            logger.warning("Cognitive loop is already running")
            return

        self.running = True
        self.state = CognitiveState.THINKING
        self.start_time = time.time()
        logger.info("Cognitive loop started")

        # Run the main loop
        await self._loop()

    async def stop(self) -> None:
        """Stop the cognitive loop."""
        self.running = False
        self.state = CognitiveState.STOPPED
        logger.info("Cognitive loop stopped")

    async def add_perception(self, data: dict[str, Any]) -> None:
        """
        Add perception data to the queue.

        Args:
            data: Perception data (commands, messages, events, etc.)
        """
        await self.perception_queue.put(data)
        logger.debug(f"Added perception to queue: {data.get('type', 'unknown')}")

    async def _loop(self) -> None:
        """Main cognitive loop."""
        while self.running and self.iteration_count < self.max_iterations:
            loop_start = time.time()
            iteration_success = True
            decision_start = time.time()

            try:
                self.iteration_count += 1

                # Update uptime metric
                if self.start_time:
                    uptime = time.time() - self.start_time
                    self.metrics.update_agent_uptime(uptime)

                # Phase 1: Perception
                self.current_phase = LoopPhase.PERCEPTION
                perception_data = await self._perceive()

                # Phase 2: Interpretation
                self.current_phase = LoopPhase.INTERPRETATION
                context = await self._interpret(perception_data)

                # Phase 3: Planning
                self.current_phase = LoopPhase.PLANNING
                plan = await self._plan(context)

                # Phase 4: Execution
                if plan:
                    self.current_phase = LoopPhase.EXECUTION
                    self.state = CognitiveState.ACTING
                    
                    # Record decision latency (perception to execution start)
                    decision_latency = time.time() - decision_start
                    self.metrics.record_decision_latency(decision_latency)
                    
                    result = await self._execute(plan)

                    # Track task success
                    task_success = result.get("success", False)
                    self.metrics.record_task_result(task_success)
                    self._update_task_success_rate(task_success)

                    # Phase 5: Reflection
                    self.current_phase = LoopPhase.REFLECTION
                    self.state = CognitiveState.REFLECTING
                    await self._reflect(result)

                # Small delay between iterations
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error in cognitive loop: {e}", exc_info=True)
                iteration_success = False
                await asyncio.sleep(1)  # Prevent tight error loop

            finally:
                # Record cognitive loop duration and status
                loop_duration = time.time() - loop_start
                status = "success" if iteration_success else "error"
                self.metrics.record_cognitive_loop(loop_duration, status)

        logger.info(f"Cognitive loop ended after {self.iteration_count} iterations")

    async def _perceive(self) -> dict[str, Any]:
        """
        Perception phase: Gather inputs.

        Returns:
            Perception data
        """
        inputs: list[Any] = []
        active_goal: dict[str, Any] | None = None
        perception: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "inputs": inputs,
            "active_goal": active_goal,
        }

        # Collect all available perceptions (non-blocking)
        while not self.perception_queue.empty():
            try:
                data = await asyncio.wait_for(self.perception_queue.get(), timeout=0.1)
                inputs.append(data)
            except asyncio.TimeoutError:
                break

        # Get current active goal
        active_goal_obj = self.goal_engine.get_active_goal()
        if active_goal_obj:
            active_goal = active_goal_obj.to_dict()
            perception["active_goal"] = active_goal

        return perception

    async def _interpret(self, perception: dict[str, Any]) -> dict[str, Any]:
        """
        Interpretation phase: Understand what the perception means.

        Args:
            perception: Perception data

        Returns:
            Interpreted context
        """
        context = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_goal": perception.get("active_goal"),
            "inputs": perception.get("inputs", []),
            "memory_context": {},
        }

        # Load relevant memory context
        active_goal = perception.get("active_goal")
        if active_goal:
            # Get recent actions for this goal
            recent_actions = await self.memory.get(f"goal:{active_goal['id']}:actions")
            if recent_actions:
                context["memory_context"]["recent_actions"] = recent_actions

        # Process inputs
        for input_data in perception.get("inputs", []):
            input_type = input_data.get("type")

            if input_type == "command":
                # High priority - user command
                context["priority"] = "high"
                context["command"] = input_data.get("content")

            elif input_type == "feedback":
                # User feedback on current work
                context["feedback"] = input_data.get("content")

            elif input_type == "event":
                # System event
                context["event"] = input_data.get("content")

        return context

    async def _plan(self, context: dict[str, Any]) -> dict[str, Any] | None:
        """
        Planning phase: Create action plan.

        Args:
            context: Interpreted context

        Returns:
            Action plan or None
        """
        # Check if we have an active goal
        active_goal = context.get("active_goal")

        # If user command, create new goal or update existing
        if context.get("command"):
            return {
                "type": "create_goal",
                "content": context["command"],
            }

        # If no active goal, check for next goal
        if not active_goal:
            next_goal = self.goal_engine.get_next_goal()
            if next_goal:
                self.goal_engine.set_active_goal(next_goal.id)
                return {
                    "type": "start_goal",
                    "goal_id": next_goal.id,
                }
            return None

        # Use planner to generate action plan
        plan = await self.planner.create_plan(context)
        return cast(dict[str, Any] | None, plan)

    async def _execute(self, plan: dict[str, Any]) -> dict[str, Any]:
        """
        Execution phase: Execute the plan.

        Args:
            plan: Action plan

        Returns:
            Execution result
        """
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "plan": plan,
            "success": False,
            "output": None,
            "error": None,
        }

        try:
            # Execute the plan
            output = await self.executor.execute(plan)
            result["success"] = True
            result["output"] = output

        except Exception as e:
            logger.error(f"Execution error: {e}")
            result["error"] = str(e)

        return result

    async def _reflect(self, result: dict[str, Any]) -> None:
        """
        Reflection phase: Evaluate results and update memory.

        Args:
            result: Execution result
        """
        # Evaluate result
        success = result.get("success", False)

        # Update memory
        await self.memory.save_short_term(
            f"last_action:{self.iteration_count}",
            result,
            ttl=3600,
        )

        # Check goal progress
        active_goal = self.goal_engine.get_active_goal()
        if active_goal:
            # Store action in goal history
            goal_actions = await self.memory.get(f"goal:{active_goal.id}:actions") or []
            goal_actions.append(
                {
                    "iteration": self.iteration_count,
                    "result": result,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            await self.memory.save_medium_term(
                f"goal:{active_goal.id}:actions",
                goal_actions,
            )

            # Check if goal is completed
            if success and self.goal_engine.check_goal_completion(active_goal.id):
                self.goal_engine.update_goal_status(active_goal.id, GoalStatus.COMPLETED)
                logger.info(f"Goal completed: {active_goal.id}")

        # Log reflection
        logger.debug(f"Reflection - Success: {success}, Iteration: {self.iteration_count}")

    def _update_task_success_rate(self, success: bool) -> None:
        """
        Update the rolling task success rate.
        
        Keeps track of the last 100 task results and calculates success rate.
        
        Args:
            success: Whether the task succeeded
        """
        # Add to results list
        self.task_results.append(success)
        
        # Keep only last 100 results
        if len(self.task_results) > 100:
            self.task_results = self.task_results[-100:]
        
        # Calculate success rate
        if self.task_results:
            success_rate = (sum(1 for r in self.task_results if r) / len(self.task_results)) * 100
            self.metrics.update_task_success_rate(success_rate)
