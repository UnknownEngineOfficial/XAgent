"""Meta-Cognition Monitor - Self-monitoring and evaluation."""

from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any

from xagent.core.learning import StrategyLearner
from xagent.utils.logging import get_logger

logger = get_logger(__name__)


class MetaCognitionMonitor:
    """
    Meta-Cognition Monitor - Self-awareness and self-correction.

    Monitors agent performance, detects problems, and triggers corrections.
    """

    def __init__(self, window_size: int = 100, enable_learning: bool = True) -> None:
        """
        Initialize meta-cognition monitor.

        Args:
            window_size: Size of performance history window
            enable_learning: Whether to enable strategy learning (emergent intelligence)
        """
        self.window_size = window_size
        self.performance_history: deque[dict[str, Any]] = deque(maxlen=window_size)
        self.error_patterns: dict[str, int] = {}
        self.loop_detection: dict[str, list[datetime]] = {}
        
        # Emergent intelligence: Strategy learning
        self.enable_learning = enable_learning
        self.strategy_learner: StrategyLearner | None = None
        if enable_learning:
            self.strategy_learner = StrategyLearner()

    def evaluate(self, result: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Evaluate an action result.

        Args:
            result: Action result to evaluate
            context: Optional context for learning

        Returns:
            Evaluation metrics
        """
        issues_detected: list[dict[str, Any]] = []
        recommendations: list[str] = []
        evaluation = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success_rate": 0.0,
            "efficiency": 0.0,
            "issues_detected": issues_detected,
            "recommendations": recommendations,
        }

        # Add to performance history
        success = result.get("success", False)
        action_type = result.get("plan", {}).get("type")
        
        self.performance_history.append(
            {
                "timestamp": datetime.now(timezone.utc),
                "success": success,
                "action_type": action_type,
            }
        )

        # Calculate success rate
        if self.performance_history:
            successes = sum(1 for r in self.performance_history if r.get("success"))
            evaluation["success_rate"] = successes / len(self.performance_history)
        
        # Record strategy execution for learning (emergent intelligence)
        if self.strategy_learner and action_type and context:
            quality_score = result.get("quality_score", 0.5)
            duration = result.get("duration", 0.0)
            
            self.strategy_learner.record_strategy_execution(
                strategy_type=action_type,
                context=context,
                success=success,
                duration=duration,
                quality_score=quality_score,
            )

        # Detect error patterns
        if not result.get("success"):
            error = result.get("error", "unknown")
            self.error_patterns[error] = self.error_patterns.get(error, 0) + 1

            if self.error_patterns[error] > 3:
                issues_detected.append(
                    {
                        "type": "repeated_error",
                        "error": error,
                        "count": self.error_patterns[error],
                    }
                )
                recommendations.append("Consider alternative approach - repeated errors detected")

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
                issues_detected.append(
                    {
                        "type": "potential_loop",
                        "action": action_type,
                        "frequency": len(recent_actions),
                    }
                )
                recommendations.append("Potential infinite loop detected - consider changing strategy")

        # Calculate efficiency (placeholder)
        success_rate = evaluation.get("success_rate", 0.0)
        if isinstance(success_rate, (int, float)):
            evaluation["efficiency"] = min(float(success_rate) * 1.2, 1.0)
        else:
            evaluation["efficiency"] = 0.0

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

    def get_strategy_recommendation(
        self, context: dict[str, Any], available_strategies: list[str] | None = None
    ) -> str | None:
        """
        Get recommended strategy based on learned patterns.
        
        Args:
            context: Current context
            available_strategies: Optional list of available strategies
        
        Returns:
            Recommended strategy or None
        """
        if not self.strategy_learner:
            return None
        
        return self.strategy_learner.get_best_strategy(context, available_strategies)

    def get_learning_insights(self) -> dict[str, Any]:
        """
        Get insights from strategy learning.
        
        Returns:
            Dictionary containing learning insights
        """
        if not self.strategy_learner:
            return {"learning_enabled": False}
        
        return {
            "learning_enabled": True,
            "strategy_statistics": self.strategy_learner.get_strategy_statistics(),
            "identified_patterns": self.strategy_learner.identify_patterns(),
        }

    def reset_monitoring(self) -> None:
        """Reset monitoring state."""
        self.performance_history.clear()
        self.error_patterns.clear()
        self.loop_detection.clear()
        
        if self.strategy_learner:
            self.strategy_learner.reset_learning()
        
        logger.info("Meta-cognition monitoring reset")
