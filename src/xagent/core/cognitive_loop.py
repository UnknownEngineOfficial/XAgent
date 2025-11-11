"""Cognitive Loop - The continuous thinking process of X-Agent."""

import asyncio
import json
import pickle
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
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

        # Checkpoint configuration
        self.checkpoint_enabled = getattr(settings, "checkpoint_enabled", True)
        self.checkpoint_interval = getattr(settings, "checkpoint_interval", 10)  # Every 10 iterations
        self.checkpoint_dir = Path(getattr(settings, "checkpoint_dir", "/tmp/xagent_checkpoints"))
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.last_checkpoint_iteration = 0

    async def start(self, resume_from_checkpoint: bool = True) -> None:
        """
        Start the cognitive loop.
        
        Args:
            resume_from_checkpoint: If True, attempt to resume from last checkpoint
        """
        if self.running:
            logger.warning("Cognitive loop is already running")
            return

        # Try to load checkpoint if requested
        checkpoint_loaded = False
        if resume_from_checkpoint:
            checkpoint_loaded = await self.load_checkpoint()
            if checkpoint_loaded:
                logger.info("Resumed from checkpoint")

        self.running = True
        self.state = CognitiveState.THINKING
        
        # Only reset start_time if not loaded from checkpoint
        if not checkpoint_loaded or self.start_time is None:
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

                # Save checkpoint if needed
                if self.should_checkpoint():
                    await self.save_checkpoint()

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

    def _get_checkpoint_state(self) -> dict[str, Any]:
        """
        Get current state for checkpointing.
        
        Returns:
            Dictionary containing checkpoint state
        """
        return {
            "iteration_count": self.iteration_count,
            "state": self.state.value,
            "current_phase": self.current_phase.value,
            "start_time": self.start_time,
            "task_results": self.task_results,
            "last_checkpoint_iteration": self.last_checkpoint_iteration,
            "active_goal_id": self.goal_engine.active_goal_id if hasattr(self.goal_engine, "active_goal_id") else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def save_checkpoint(self) -> None:
        """
        Save current state to checkpoint file.
        
        Saves both JSON (metadata) and pickle (full state) formats.
        """
        if not self.checkpoint_enabled:
            return

        try:
            # Ensure checkpoint directory exists
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
            
            checkpoint_state = self._get_checkpoint_state()
            
            # Save as JSON for readability
            json_path = self.checkpoint_dir / "checkpoint.json"
            with open(json_path, "w") as f:
                json.dump(checkpoint_state, f, indent=2)
            
            # Save full state with pickle for complete restoration
            pickle_path = self.checkpoint_dir / "checkpoint.pkl"
            with open(pickle_path, "wb") as f:
                pickle.dump(checkpoint_state, f)
            
            self.last_checkpoint_iteration = self.iteration_count
            logger.info(f"Checkpoint saved at iteration {self.iteration_count}")
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}", exc_info=True)

    async def load_checkpoint(self) -> bool:
        """
        Load state from checkpoint file.
        
        Returns:
            True if checkpoint was loaded successfully, False otherwise
        """
        if not self.checkpoint_enabled:
            return False

        try:
            # Try to load from pickle first (more complete)
            pickle_path = self.checkpoint_dir / "checkpoint.pkl"
            if pickle_path.exists():
                with open(pickle_path, "rb") as f:
                    checkpoint_state = pickle.load(f)
                
                # Restore state
                self.iteration_count = checkpoint_state.get("iteration_count", 0)
                self.state = CognitiveState(checkpoint_state.get("state", "idle"))
                self.current_phase = LoopPhase(checkpoint_state.get("current_phase", "perception"))
                self.start_time = checkpoint_state.get("start_time")
                self.task_results = checkpoint_state.get("task_results", [])
                self.last_checkpoint_iteration = checkpoint_state.get("last_checkpoint_iteration", 0)
                
                # Restore active goal if available
                active_goal_id = checkpoint_state.get("active_goal_id")
                if active_goal_id and hasattr(self.goal_engine, "set_active_goal"):
                    self.goal_engine.set_active_goal(active_goal_id)
                
                logger.info(f"Checkpoint loaded from iteration {self.iteration_count}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}", exc_info=True)
        
        return False

    def should_checkpoint(self) -> bool:
        """
        Determine if a checkpoint should be saved.
        
        Returns:
            True if checkpoint should be saved
        """
        if not self.checkpoint_enabled:
            return False
        
        iterations_since_last = self.iteration_count - self.last_checkpoint_iteration
        return iterations_since_last >= self.checkpoint_interval
