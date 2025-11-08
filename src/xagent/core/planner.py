"""Planner - Strategic planning for X-Agent."""

import json
from datetime import datetime, timezone
from typing import Any

from xagent.utils.logging import get_logger

logger = get_logger(__name__)


class Planner:
    """
    Planner creates strategic action plans based on goals and context.

    Uses LLM-based reasoning to generate step-by-step plans.
    """

    def __init__(self, llm_client: Any | None = None) -> None:
        """
        Initialize planner.

        Args:
            llm_client: LLM client for planning (OpenAI, Anthropic, etc.)
        """
        self.llm_client = llm_client

    async def create_plan(self, context: dict[str, Any]) -> dict[str, Any] | None:
        """
        Create an action plan based on context.

        Args:
            context: Current context including goals, memory, inputs

        Returns:
            Action plan or None
        """
        active_goal = context.get("active_goal")
        if not active_goal:
            return None

        # Build planning prompt
        prompt = self._build_planning_prompt(context)

        # If LLM client is available, use it for planning
        if self.llm_client:
            plan = await self._llm_based_planning(prompt, context)
        else:
            # Simple rule-based planning as fallback
            plan = self._rule_based_planning(context)

        return plan

    def _build_planning_prompt(self, context: dict[str, Any]) -> str:
        """Build planning prompt for LLM."""
        active_goal = context.get("active_goal", {})

        prompt = f"""You are an autonomous agent planning the next action.

Current Goal: {active_goal.get('description', 'No active goal')}
Goal Mode: {active_goal.get('mode', 'unknown')}
Goal Status: {active_goal.get('status', 'unknown')}

Context:
- Recent Actions: {json.dumps(context.get('memory_context', {}).get('recent_actions', []))}
- User Feedback: {context.get('feedback', 'None')}
- Events: {context.get('event', 'None')}

Completion Criteria:
{json.dumps(active_goal.get('completion_criteria', []), indent=2)}

Based on this context, what is the next best action to take?
Provide your response as a JSON object with the following structure:
{{
    "type": "action_type",
    "action": "specific_action",
    "parameters": {{}},
    "reasoning": "why this action"
}}
"""
        return prompt

    async def _llm_based_planning(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Use LLM for intelligent planning.

        Args:
            prompt: Planning prompt
            context: Current context

        Returns:
            Action plan
        """
        # This would use the actual LLM client
        # For now, fallback to rule-based
        logger.info("LLM-based planning not yet implemented, using rule-based")
        return self._rule_based_planning(context)

    def _rule_based_planning(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Simple rule-based planning.

        Args:
            context: Current context

        Returns:
            Action plan
        """
        active_goal = context.get("active_goal", {})

        # Simple planning logic
        plan = {
            "type": "think",
            "action": "analyze_goal",
            "parameters": {
                "goal_id": active_goal.get("id"),
                "goal_description": active_goal.get("description"),
            },
            "reasoning": "Analyzing current goal to determine next steps",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return plan

    def decompose_goal(self, goal: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Decompose a goal into sub-goals.

        Args:
            goal: Goal to decompose

        Returns:
            List of sub-goals
        """
        # This would use LLM to intelligently decompose goals
        # For now, return empty list
        return []

    def evaluate_plan_quality(self, plan: dict[str, Any]) -> float:
        """
        Evaluate the quality of a plan.

        Args:
            plan: Plan to evaluate

        Returns:
            Quality score (0-1)
        """
        # Simple heuristic - check if plan has required fields
        required_fields = ["type", "action", "parameters"]
        score = sum(1 for field in required_fields if field in plan) / len(required_fields)
        return score
