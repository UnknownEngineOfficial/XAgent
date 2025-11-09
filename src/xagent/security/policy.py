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
            Supports logical expressions with AND, OR, NOT operators and
            nested conditions using parentheses.

        Examples:
            - "delete": matches if "delete" in context
            - "delete AND system": matches if both present
            - "delete OR remove": matches if either present
            - "NOT test": matches if "test" not present
            - "(delete OR remove) AND system": complex nested logic
        """
        if self.condition is None:
            return True

        # Empty condition string should not match
        if not self.condition.strip():
            return False

        # Evaluate the condition expression
        return self._evaluate_expression(self.condition, context)

    def _evaluate_expression(self, expression: str, context: dict[str, Any]) -> bool:
        """
        Evaluate a logical expression with AND, OR, NOT operators.

        Args:
            expression: Logical expression to evaluate
            context: Execution context

        Returns:
            Evaluation result
        """
        # Normalize context to string for matching
        context_str = str(context).lower()
        expression = expression.strip()

        # Handle special placeholders from parentheses evaluation
        if expression == "__EXPR_TRUE__":
            return True
        if expression == "__EXPR_FALSE__":
            return False

        # Handle NOT operator (highest precedence)
        if expression.upper().startswith("NOT "):
            sub_expr = expression[4:].strip()
            return not self._evaluate_expression(sub_expr, context)

        # Handle parentheses (group expressions)
        if "(" in expression:
            return self._evaluate_with_parentheses(expression, context)

        # Handle OR operator (lower precedence than AND)
        if " OR " in expression.upper():
            parts = self._split_by_operator(expression, "OR")
            return any(self._evaluate_expression(part, context) for part in parts)

        # Handle AND operator (higher precedence than OR)
        if " AND " in expression.upper():
            parts = self._split_by_operator(expression, "AND")
            return all(self._evaluate_expression(part, context) for part in parts)

        # Base case: simple keyword matching
        keyword = expression.strip().lower()
        return keyword in context_str

    def _split_by_operator(self, expression: str, operator: str) -> list[str]:
        """Split expression by operator while preserving case."""
        parts = []
        current = []
        tokens = expression.split()

        for token in tokens:
            if token.upper() == operator:
                if current:
                    parts.append(" ".join(current))
                    current = []
            else:
                current.append(token)

        if current:
            parts.append(" ".join(current))

        return parts

    def _evaluate_with_parentheses(self, expression: str, context: dict[str, Any]) -> bool:
        """
        Evaluate expression with nested parentheses.

        Args:
            expression: Expression with parentheses
            context: Execution context

        Returns:
            Evaluation result
        """
        # Find and evaluate innermost parentheses first
        while "(" in expression:
            # Find the last opening parenthesis (innermost)
            start = expression.rfind("(")
            # Find its matching closing parenthesis
            end = expression.find(")", start)

            if end == -1:
                # Unmatched parenthesis, treat as regular expression
                logger.warning(f"Unmatched parenthesis in expression: {expression}")
                return self._evaluate_expression(
                    expression.replace("(", "").replace(")", ""), context
                )

            # Extract and evaluate the sub-expression
            sub_expr = expression[start + 1 : end]
            sub_result = self._evaluate_expression(sub_expr, context)

            # Replace the parenthesized expression with its boolean result as a keyword
            # Use unique placeholders that represent the boolean values
            placeholder = " __EXPR_TRUE__ " if sub_result else " __EXPR_FALSE__ "
            expression = expression[:start] + placeholder + expression[end + 1 :]

        # Now the expression only has placeholders and operators
        # Evaluate the remaining expression treating placeholders as keywords
        # that always/never match

        # Replace __EXPR_TRUE__ with a keyword that's always in context
        # Replace __EXPR_FALSE__ with a keyword that's never in context
        expression = expression.strip()

        # Handle the simplified expression with true/false placeholders
        if "__EXPR_TRUE__" in expression and "__EXPR_FALSE__" not in expression:
            # Only true values, check operators
            if " AND " in expression.upper():
                # All must be true or match
                parts = self._split_by_operator(expression, "AND")
                return all(
                    p.strip() == "__EXPR_TRUE__" or self._evaluate_expression(p, context)
                    for p in parts
                )
            elif " OR " in expression.upper():
                # At least one true is enough
                return True
            else:
                # Single true value
                return expression.strip() == "__EXPR_TRUE__"

        elif "__EXPR_FALSE__" in expression and "__EXPR_TRUE__" not in expression:
            # Only false values
            if " OR " in expression.upper():
                # Check if any non-placeholder matches
                parts = self._split_by_operator(expression, "OR")
                return any(
                    p.strip() != "__EXPR_FALSE__" and self._evaluate_expression(p, context)
                    for p in parts
                )
            elif " AND " in expression.upper():
                # If any is false, whole is false
                return False
            else:
                # Single false value
                return False

        elif "__EXPR_TRUE__" in expression or "__EXPR_FALSE__" in expression:
            # Mix of true and false
            # Evaluate the full expression with special handling for placeholders

            # For __EXPR_TRUE__, we know it evaluates to True
            # For __EXPR_FALSE__, we know it evaluates to False
            # Evaluate the expression with these known values

            # Handle OR first (lower precedence)
            if " OR " in expression.upper():
                # If any __EXPR_TRUE__ exists, could be true depending on operator
                parts = self._split_by_operator(expression, "OR")
                for part in parts:
                    part = part.strip()
                    if part == "__EXPR_TRUE__":
                        return True
                    elif part != "__EXPR_FALSE__":
                        # Regular expression
                        if self._evaluate_expression(part, context):
                            return True
                return False  # No true parts found

            # Handle AND (higher precedence)
            if " AND " in expression.upper():
                parts = self._split_by_operator(expression, "AND")
                for part in parts:
                    part = part.strip()
                    if part == "__EXPR_FALSE__":
                        return False
                    elif part != "__EXPR_TRUE__":
                        # Regular expression
                        if not self._evaluate_expression(part, context):
                            return False
                return True  # All parts are true

        # No placeholders, shouldn't reach here but evaluate safely
        return self._evaluate_expression(expression, context)


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
