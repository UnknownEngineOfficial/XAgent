"""Security policy layer for X-Agent."""

from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from xagent.utils.logging import get_logger

logger = get_logger(__name__)


class PolicyAction(str, Enum):
    """Policy action types."""

    ALLOW = "allow"
    BLOCK = "block"
    REQUIRE_CONFIRMATION = "require_confirmation"


class PolicyRule:
    """Security policy rule."""

    def __init__(
        self,
        name: str,
        action: PolicyAction,
        condition: str | None = None,
        message: str | None = None,
    ) -> None:
        """Initialize policy rule."""
        self.name = name
        self.action = action
        self.condition = condition
        self.message = message

    def evaluate(self, context: dict[str, Any]) -> bool:
        """
        Evaluate if rule applies to context.

        Args:
            context: Execution context

        Returns:
            True if rule applies, False otherwise

        Note:
            This is a simplified implementation for demonstration.
            Production systems should use proper expression parsing or rule engines.
        """
        if not self.condition:
            return True

        # Simple keyword matching for demonstration
        # TODO: Implement proper rule engine for production
        context_str = str(context).lower()
        condition_keywords = self.condition.lower().split()

        return any(keyword in context_str for keyword in condition_keywords)


class PolicyLayer:
    """
    Security policy layer.

    Enforces security rules and constraints on agent actions.
    """

    def __init__(self, policy_file: Path | None = None) -> None:
        """
        Initialize policy layer.

        Args:
            policy_file: Path to policy YAML file
        """
        self.rules: list[PolicyRule] = []

        if policy_file and policy_file.exists():
            self.load_policies(policy_file)
        else:
            # Load default policies
            self.load_default_policies()

    def load_policies(self, policy_file: Path) -> None:
        """Load policies from YAML file."""
        try:
            with open(policy_file) as f:
                data = yaml.safe_load(f)

            rules_data = data.get("rules", [])

            for rule_data in rules_data:
                rule = PolicyRule(
                    name=rule_data["name"],
                    action=PolicyAction(rule_data["type"]),
                    condition=rule_data.get("condition"),
                    message=rule_data.get("message"),
                )
                self.rules.append(rule)

            logger.info(f"Loaded {len(self.rules)} policy rules from {policy_file}")

        except Exception as e:
            logger.error(f"Failed to load policies: {e}")
            self.load_default_policies()

    def load_default_policies(self) -> None:
        """Load default security policies."""
        default_rules = [
            PolicyRule(
                name="no_delete_without_confirmation",
                action=PolicyAction.REQUIRE_CONFIRMATION,
                condition="delete",
                message="Deletion requires confirmation",
            ),
            PolicyRule(
                name="no_system_modification",
                action=PolicyAction.BLOCK,
                condition="system modify",
                message="System modification is blocked",
            ),
            PolicyRule(
                name="rate_limit_api_calls",
                action=PolicyAction.BLOCK,
                condition="api excessive",
                message="API rate limit exceeded",
            ),
        ]

        self.rules.extend(default_rules)
        logger.info(f"Loaded {len(default_rules)} default policy rules")

    def check_action(self, action: dict[str, Any]) -> dict[str, Any]:
        """
        Check if an action is allowed by policies.

        Args:
            action: Action to check

        Returns:
            Policy decision with action and message
        """
        for rule in self.rules:
            if rule.evaluate(action):
                return {
                    "allowed": rule.action == PolicyAction.ALLOW,
                    "requires_confirmation": rule.action == PolicyAction.REQUIRE_CONFIRMATION,
                    "blocked": rule.action == PolicyAction.BLOCK,
                    "rule": rule.name,
                    "message": rule.message or f"Action subject to rule: {rule.name}",
                }

        # Default: allow if no blocking rule matches
        return {
            "allowed": True,
            "requires_confirmation": False,
            "blocked": False,
            "rule": None,
            "message": "No policy restrictions",
        }

    def add_rule(self, rule: PolicyRule) -> None:
        """Add a new policy rule."""
        self.rules.append(rule)
        logger.info(f"Added policy rule: {rule.name}")

    def remove_rule(self, rule_name: str) -> None:
        """Remove a policy rule."""
        self.rules = [r for r in self.rules if r.name != rule_name]
        logger.info(f"Removed policy rule: {rule_name}")
