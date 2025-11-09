"""LangGraph-based Planner for X-Agent.

This module provides an enhanced planner using LangGraph for complex planning workflows
with state management and conditional routing.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, TypedDict, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import END, StateGraph

from xagent.utils.logging import get_logger

logger = get_logger(__name__)


class PlanningPhase(str, Enum):
    """Planning workflow phases."""

    ANALYZE = "analyze"
    DECOMPOSE = "decompose"
    PRIORITIZE = "prioritize"
    VALIDATE = "validate"
    EXECUTE = "execute"


class PlanningState(TypedDict):
    """State for the planning workflow."""

    # Input
    goal_description: str
    goal_id: str
    goal_mode: str
    completion_criteria: list[str]
    context: dict[str, Any]

    # Workflow state
    current_phase: str
    messages: list[BaseMessage]

    # Analysis results
    goal_complexity: str | None
    required_capabilities: list[str]
    estimated_steps: int | None

    # Decomposition results
    sub_goals: list[dict[str, Any]]
    dependencies: list[dict[str, str]]

    # Prioritization results
    prioritized_actions: list[dict[str, Any]]

    # Final plan
    plan: dict[str, Any] | None
    quality_score: float | None

    # Error handling
    errors: list[str]


class LangGraphPlanner:
    """
    Enhanced planner using LangGraph for complex planning workflows.

    This planner implements a multi-stage planning process:
    1. Analyze: Understand goal complexity and requirements
    2. Decompose: Break down complex goals into sub-goals
    3. Prioritize: Order actions by importance and dependencies
    4. Validate: Check plan quality and feasibility
    5. Execute: Generate final actionable plan
    """

    def __init__(self, llm: BaseChatModel | None = None) -> None:
        """
        Initialize LangGraph planner.

        Args:
            llm: Language model for planning (optional, will use rule-based if None)
        """
        self.llm = llm
        self.graph = self._build_planning_graph()

    def _build_planning_graph(self) -> Any:
        """Build the LangGraph planning workflow."""
        workflow = StateGraph(PlanningState)

        # Add nodes for each planning phase
        workflow.add_node("analyze", self._analyze_goal)
        workflow.add_node("decompose", self._decompose_goal)
        workflow.add_node("prioritize", self._prioritize_actions)
        workflow.add_node("validate", self._validate_plan)
        workflow.add_node("execute", self._execute_plan)

        # Define edges (workflow transitions)
        workflow.set_entry_point("analyze")
        workflow.add_edge("analyze", "decompose")
        workflow.add_conditional_edges(
            "decompose",
            self._should_continue_to_prioritize,
            {
                "prioritize": "prioritize",
                "validate": "validate",  # Skip to validate if no decomposition needed
            },
        )
        workflow.add_edge("prioritize", "validate")
        workflow.add_conditional_edges(
            "validate",
            self._should_replan,
            {
                "execute": "execute",
                "analyze": "analyze",  # Re-plan if validation fails
            },
        )
        workflow.add_edge("execute", END)

        return workflow.compile()

    async def create_plan(self, context: dict[str, Any]) -> dict[str, Any] | None:
        """
        Create an action plan using LangGraph workflow.

        Args:
            context: Current context including goals, memory, inputs

        Returns:
            Action plan or None
        """
        active_goal = context.get("active_goal")
        if not active_goal:
            logger.warning("No active goal in context")
            return None

        # Initialize planning state
        initial_state: PlanningState = {
            "goal_description": active_goal.get("description", ""),
            "goal_id": active_goal.get("id", ""),
            "goal_mode": active_goal.get("mode", "goal_oriented"),
            "completion_criteria": active_goal.get("completion_criteria", []),
            "context": context,
            "current_phase": "analyze",
            "messages": [],
            "goal_complexity": None,
            "required_capabilities": [],
            "estimated_steps": None,
            "sub_goals": [],
            "dependencies": [],
            "prioritized_actions": [],
            "plan": None,
            "quality_score": None,
            "errors": [],
        }

        try:
            # Run the planning workflow
            result = await self.graph.ainvoke(initial_state)
            return cast(dict[str, Any] | None, result.get("plan"))
        except Exception as e:
            logger.error(f"Planning workflow failed: {e}", exc_info=True)
            return self._fallback_plan(context)

    async def _analyze_goal(self, state: PlanningState) -> PlanningState:
        """Analyze goal complexity and requirements."""
        logger.info(f"Analyzing goal: {state['goal_id']}")

        state["current_phase"] = PlanningPhase.ANALYZE.value

        # Determine goal complexity based on description and criteria
        description = state["goal_description"].lower()
        criteria_count = len(state["completion_criteria"])

        # Simple heuristic for complexity
        if criteria_count >= 5 or len(description.split()) > 50:
            complexity = "high"
            estimated_steps = 8
        elif criteria_count >= 3 or len(description.split()) > 20:
            complexity = "medium"
            estimated_steps = 4
        else:
            complexity = "low"
            estimated_steps = 2

        state["goal_complexity"] = complexity
        state["estimated_steps"] = estimated_steps

        # Identify required capabilities based on keywords
        capabilities = []
        if any(word in description for word in ["code", "program", "script", "function"]):
            capabilities.append("code_execution")
        if any(word in description for word in ["file", "write", "read", "save"]):
            capabilities.append("file_operations")
        if any(word in description for word in ["web", "search", "fetch", "api"]):
            capabilities.append("web_access")
        if any(word in description for word in ["calculate", "compute", "analyze"]):
            capabilities.append("computation")

        state["required_capabilities"] = capabilities

        # Add analysis message
        state["messages"].append(
            SystemMessage(
                content=f"Goal analyzed: complexity={complexity}, steps~{estimated_steps}"
            )
        )

        logger.info(f"Analysis complete: complexity={complexity}, capabilities={capabilities}")
        return state

    async def _decompose_goal(self, state: PlanningState) -> PlanningState:
        """Decompose complex goals into sub-goals."""
        logger.info(f"Decomposing goal: {state['goal_id']}")

        state["current_phase"] = PlanningPhase.DECOMPOSE.value

        # Only decompose medium/high complexity goals
        if state["goal_complexity"] in ["medium", "high"]:
            sub_goals = []

            # Create sub-goals based on completion criteria
            for i, criterion in enumerate(state["completion_criteria"]):
                sub_goal = {
                    "id": f"{state['goal_id']}_sub_{i}",
                    "description": f"Achieve: {criterion}",
                    "priority": i,
                    "estimated_effort": 1,
                }
                sub_goals.append(sub_goal)

            # If no criteria, create default sub-goals based on required capabilities
            if not sub_goals and state["required_capabilities"]:
                for i, capability in enumerate(state["required_capabilities"]):
                    sub_goal = {
                        "id": f"{state['goal_id']}_sub_{i}",
                        "description": f"Use {capability} to progress on goal",
                        "priority": i,
                        "estimated_effort": 1,
                    }
                    sub_goals.append(sub_goal)

            state["sub_goals"] = sub_goals

            # Create simple sequential dependencies
            dependencies = []
            for i in range(1, len(sub_goals)):
                dependencies.append(
                    {"from": sub_goals[i - 1]["id"], "to": sub_goals[i]["id"], "type": "sequential"}
                )
            state["dependencies"] = dependencies

            logger.info(f"Decomposed into {len(sub_goals)} sub-goals")
        else:
            logger.info("Goal complexity low, skipping decomposition")

        return state

    async def _prioritize_actions(self, state: PlanningState) -> PlanningState:
        """Prioritize actions based on dependencies and importance."""
        logger.info("Prioritizing actions")

        state["current_phase"] = PlanningPhase.PRIORITIZE.value

        # Prioritize sub-goals if they exist
        if state["sub_goals"]:
            # Sort by priority (already set in decomposition)
            prioritized = sorted(state["sub_goals"], key=lambda x: x["priority"])

            # Convert to actions
            actions = []
            for sub_goal in prioritized:
                action = {
                    "type": "sub_goal",
                    "action": "work_on_sub_goal",
                    "parameters": {
                        "sub_goal_id": sub_goal["id"],
                        "description": sub_goal["description"],
                    },
                    "priority": sub_goal["priority"],
                    "reasoning": f"Sub-goal with priority {sub_goal['priority']}",
                }
                actions.append(action)
        else:
            # No sub-goals, create single action
            actions = [
                {
                    "type": "direct",
                    "action": "work_on_goal",
                    "parameters": {
                        "goal_id": state["goal_id"],
                        "description": state["goal_description"],
                    },
                    "priority": 0,
                    "reasoning": "Direct goal execution without decomposition",
                }
            ]

        state["prioritized_actions"] = actions
        logger.info(f"Prioritized {len(actions)} actions")

        return state

    async def _validate_plan(self, state: PlanningState) -> PlanningState:
        """Validate plan quality and feasibility."""
        logger.info("Validating plan")

        state["current_phase"] = PlanningPhase.VALIDATE.value

        quality_score = 0.0
        errors = []

        # If we skipped prioritization, generate a simple action now
        if not state["prioritized_actions"]:
            # Create direct action for simple goals
            state["prioritized_actions"] = [
                {
                    "type": "direct",
                    "action": "work_on_goal",
                    "parameters": {
                        "goal_id": state["goal_id"],
                        "description": state["goal_description"],
                    },
                    "priority": 0,
                    "reasoning": "Direct goal execution without decomposition",
                }
            ]

        # Validate actions
        if not state["prioritized_actions"]:
            errors.append("No actions generated")
            quality_score = 0.0
        else:
            # Validate each action has required fields
            valid_actions = 0
            for action in state["prioritized_actions"]:
                if all(key in action for key in ["type", "action", "parameters"]):
                    valid_actions += 1

            quality_score = valid_actions / len(state["prioritized_actions"])

            # Check if all required capabilities are addressed
            addressed_capabilities = set()
            for action in state["prioritized_actions"]:
                params = action.get("parameters", {})
                desc = params.get("description", "").lower()

                if any(word in desc for word in ["code", "execute"]):
                    addressed_capabilities.add("code_execution")
                if any(word in desc for word in ["file", "write", "read"]):
                    addressed_capabilities.add("file_operations")
                if any(word in desc for word in ["web", "search", "fetch"]):
                    addressed_capabilities.add("web_access")

            # Bonus points for addressing all required capabilities
            required_caps = set(state["required_capabilities"])
            if required_caps and required_caps.issubset(addressed_capabilities):
                quality_score = min(1.0, quality_score + 0.2)

        state["quality_score"] = quality_score
        state["errors"] = errors

        logger.info(f"Validation complete: quality_score={quality_score:.2f}, errors={len(errors)}")

        return state

    async def _execute_plan(self, state: PlanningState) -> PlanningState:
        """Generate final actionable plan."""
        logger.info("Executing plan generation")

        state["current_phase"] = PlanningPhase.EXECUTE.value

        # Take the first prioritized action as the next action
        if state["prioritized_actions"]:
            next_action = state["prioritized_actions"][0]
        else:
            # Fallback action
            next_action = {
                "type": "think",
                "action": "analyze_goal",
                "parameters": {
                    "goal_id": state["goal_id"],
                    "description": state["goal_description"],
                },
                "reasoning": "Fallback action for goal analysis",
            }

        # Build final plan
        plan = {
            **next_action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "goal_id": state["goal_id"],
            "goal_complexity": state["goal_complexity"],
            "quality_score": state["quality_score"],
            "remaining_actions": len(state["prioritized_actions"]) - 1,
            "sub_goals": [sg["id"] for sg in state["sub_goals"]],
        }

        state["plan"] = plan
        logger.info(f"Plan generated: {plan['action']}")

        return state

    def _should_continue_to_prioritize(self, state: PlanningState) -> str:
        """Decide whether to continue to prioritization or skip to validation."""
        if state["sub_goals"]:
            return "prioritize"
        else:
            # Skip prioritization but go to validate to get quality score
            return "validate"

    def _should_replan(self, state: PlanningState) -> str:
        """Decide whether to execute plan or re-analyze."""
        quality_score = state.get("quality_score", 0.0)

        # If quality is too low and we haven't retried yet, re-analyze
        if quality_score < 0.3 and "replan_attempted" not in state.get("context", {}):
            logger.warning(f"Plan quality too low ({quality_score:.2f}), re-planning")
            state["context"]["replan_attempted"] = True
            return "analyze"
        else:
            return "execute"

    def _fallback_plan(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate a simple fallback plan if workflow fails."""
        active_goal = context.get("active_goal", {})

        return {
            "type": "think",
            "action": "analyze_goal",
            "parameters": {
                "goal_id": active_goal.get("id"),
                "goal_description": active_goal.get("description"),
            },
            "reasoning": "Fallback plan due to workflow error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def decompose_goal(self, goal: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Decompose a goal into sub-goals (synchronous wrapper).

        Args:
            goal: Goal to decompose

        Returns:
            List of sub-goals
        """
        # Create a minimal context for the workflow

        # Run synchronous analysis (simplified)
        goal.get("description", "").lower()
        criteria = goal.get("completion_criteria", [])

        sub_goals = []
        for i, criterion in enumerate(criteria):
            sub_goal = {
                "id": f"{goal.get('id', 'goal')}_sub_{i}",
                "description": f"Achieve: {criterion}",
                "priority": i,
                "parent_id": goal.get("id"),
            }
            sub_goals.append(sub_goal)

        return sub_goals

    def evaluate_plan_quality(self, plan: dict[str, Any]) -> float:
        """
        Evaluate the quality of a plan.

        Args:
            plan: Plan to evaluate

        Returns:
            Quality score (0-1)
        """
        # Return stored quality score if available
        if "quality_score" in plan:
            return plan["quality_score"]

        # Otherwise, use simple heuristic
        required_fields = ["type", "action", "parameters", "reasoning"]
        score = sum(1 for field in required_fields if field in plan) / len(required_fields)

        # Bonus for having sub-goals and complexity analysis
        if plan.get("sub_goals"):
            score = min(1.0, score + 0.1)
        if plan.get("goal_complexity"):
            score = min(1.0, score + 0.1)

        return score
