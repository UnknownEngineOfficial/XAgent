"""Meta-Cognition Monitor - Self-monitoring and evaluation."""

from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any

from xagent.utils.logging import get_logger

logger = get_logger(__name__)


class MetaCognitionMonitor:
    """
    Meta-Cognition Monitor - Self-awareness and self-correction.

    Monitors agent performance, detects problems, and triggers corrections.
    """

    def __init__(self, window_size: int = 100) -> None:
        """
        Initialize meta-cognition monitor.

        Args:
            window_size: Size of performance history window
        """
        self.window_size = window_size
        self.performance_history: deque = deque(maxlen=window_size)
        self.error_patterns: dict[str, int] = {}
        self.loop_detection: dict[str, list[datetime]] = {}

    def evaluate(self, result: dict[str, Any]) -> dict[str, Any]:
        """
        Evaluate an action result.

        Args:
            result: Action result to evaluate

        Returns:
            Evaluation metrics
        """
        evaluation = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success_rate": 0.0,
            "efficiency": 0.0,
            "issues_detected": [],
            "recommendations": [],
        }

        # Add to performance history
        self.performance_history.append(
            {
                "timestamp": datetime.now(timezone.utc),
                "success": result.get("success", False),
                "action_type": result.get("plan", {}).get("type"),
            }
        )

        # Calculate success rate
        if self.performance_history:
            successes = sum(1 for r in self.performance_history if r.get("success"))
            evaluation["success_rate"] = successes / len(self.performance_history)

        # Detect error patterns
        if not result.get("success"):
            error = result.get("error", "unknown")
            self.error_patterns[error] = self.error_patterns.get(error, 0) + 1

            if self.error_patterns[error] > 3:
                evaluation["issues_detected"].append(
                    {
                        "type": "repeated_error",
                        "error": error,
                        "count": self.error_patterns[error],
                    }
                )
                evaluation["recommendations"].append(
                    "Consider alternative approach - repeated errors detected"
                )

        # Detect potential loops
        action_type = result.get("plan", {}).get("type")
        if action_type:
            if action_type not in self.loop_detection:
                self.loop_detection[action_type] = []

            self.loop_detection[action_type].append(datetime.now(timezone.utc))

            # Check if same action repeated too frequently
            recent_actions = [
                t
                for t in self.loop_detection[action_type]
                if t > datetime.now(timezone.utc) - timedelta(minutes=5)
            ]

            if len(recent_actions) > 10:
                evaluation["issues_detected"].append(
                    {
                        "type": "potential_loop",
                        "action": action_type,
                        "frequency": len(recent_actions),
                    }
                )
                evaluation["recommendations"].append(
                    "Potential infinite loop detected - consider changing strategy"
                )

        # Calculate efficiency (placeholder)
        evaluation["efficiency"] = min(evaluation["success_rate"] * 1.2, 1.0)

        return evaluation

    def get_performance_summary(self) -> dict[str, Any]:
        """Get overall performance summary."""
        if not self.performance_history:
            return {
                "total_actions": 0,
                "success_rate": 0.0,
                "common_errors": [],
            }

        successes = sum(1 for r in self.performance_history if r.get("success"))

        # Get top errors
        common_errors = sorted(
            self.error_patterns.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        return {
            "total_actions": len(self.performance_history),
            "success_rate": successes / len(self.performance_history),
            "common_errors": [{"error": error, "count": count} for error, count in common_errors],
        }

    def reset_monitoring(self) -> None:
        """Reset monitoring state."""
        self.performance_history.clear()
        self.error_patterns.clear()
        self.loop_detection.clear()
        logger.info("Meta-cognition monitoring reset")
