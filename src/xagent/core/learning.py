"""Learning Module - Experience-based learning and strategy improvement.

This module implements emergent intelligence capabilities:
- Pattern recognition over agent performance
- Strategy optimization based on success rates
- Experience-based decision making
"""

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from xagent.utils.logging import get_logger

logger = get_logger(__name__)


class StrategyLearner:
    """
    Strategy learner for emergent intelligence.
    
    Learns from past experiences to improve decision-making and strategy selection.
    """

    def __init__(self, persistence_path: str | None = None) -> None:
        """
        Initialize strategy learner.
        
        Args:
            persistence_path: Optional path to persist learning data
        """
        self.persistence_path = Path(persistence_path) if persistence_path else None
        
        # Strategy performance tracking
        self.strategy_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "attempts": 0,
                "successes": 0,
                "failures": 0,
                "total_duration": 0.0,
                "avg_quality_score": 0.0,
                "context_patterns": [],
            }
        )
        
        # Pattern recognition
        self.success_patterns: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.failure_patterns: dict[str, list[dict[str, Any]]] = defaultdict(list)
        
        # Strategy recommendations
        self.strategy_recommendations: dict[str, str] = {}
        
        # Load persisted data if available
        if self.persistence_path and self.persistence_path.exists():
            self._load_learning_data()

    def record_strategy_execution(
        self,
        strategy_type: str,
        context: dict[str, Any],
        success: bool,
        duration: float = 0.0,
        quality_score: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Record a strategy execution for learning.
        
        Args:
            strategy_type: Type of strategy executed (e.g., "direct", "decompose", "think")
            context: Context in which strategy was executed
            success: Whether the strategy succeeded
            duration: Duration of execution in seconds
            quality_score: Quality score of the result (0-1)
            metadata: Additional metadata about the execution
        """
        stats = self.strategy_stats[strategy_type]
        stats["attempts"] += 1
        
        if success:
            stats["successes"] += 1
        else:
            stats["failures"] += 1
        
        stats["total_duration"] += duration
        
        # Update average quality score
        old_avg = stats["avg_quality_score"]
        attempts = stats["attempts"]
        stats["avg_quality_score"] = (old_avg * (attempts - 1) + quality_score) / attempts
        
        # Extract and store context patterns
        pattern = self._extract_context_pattern(context)
        stats["context_patterns"].append(pattern)
        
        # Store success/failure patterns
        execution_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context_pattern": pattern,
            "duration": duration,
            "quality_score": quality_score,
            "metadata": metadata or {},
        }
        
        if success:
            self.success_patterns[strategy_type].append(execution_record)
        else:
            self.failure_patterns[strategy_type].append(execution_record)
        
        # Update strategy recommendations
        self._update_recommendations()
        
        logger.debug(
            f"Recorded strategy execution: {strategy_type} "
            f"(success={success}, quality={quality_score:.2f})"
        )

    def get_best_strategy(
        self, context: dict[str, Any], available_strategies: list[str] | None = None
    ) -> str | None:
        """
        Get the best strategy recommendation for the given context.
        
        Args:
            context: Current context
            available_strategies: List of available strategies (None = all)
        
        Returns:
            Recommended strategy name or None
        """
        if not self.strategy_stats:
            return None
        
        current_pattern = self._extract_context_pattern(context)
        
        # Filter strategies
        strategies = available_strategies if available_strategies is not None else list(self.strategy_stats.keys())
        
        # Return None if empty list provided
        if not strategies:
            return None
        
        # Score each strategy
        strategy_scores: dict[str, float] = {}
        for strategy in strategies:
            if strategy not in self.strategy_stats:
                continue
            
            stats = self.strategy_stats[strategy]
            
            # Base score: success rate
            if stats["attempts"] > 0:
                success_rate = stats["successes"] / stats["attempts"]
            else:
                success_rate = 0.0
            
            # Factor in quality score
            quality_factor = stats["avg_quality_score"]
            
            # Factor in efficiency (inverse of avg duration)
            if stats["attempts"] > 0 and stats["total_duration"] > 0:
                avg_duration = stats["total_duration"] / stats["attempts"]
                efficiency_factor = 1.0 / (1.0 + avg_duration / 10.0)  # Normalize
            else:
                efficiency_factor = 0.5
            
            # Factor in pattern matching
            pattern_match_score = self._calculate_pattern_match(
                current_pattern, stats["context_patterns"]
            )
            
            # Combined score (weighted)
            combined_score = (
                0.4 * success_rate +
                0.3 * quality_factor +
                0.2 * efficiency_factor +
                0.1 * pattern_match_score
            )
            
            strategy_scores[strategy] = combined_score
            
            logger.debug(
                f"Strategy '{strategy}' score: {combined_score:.3f} "
                f"(success={success_rate:.2f}, quality={quality_factor:.2f}, "
                f"efficiency={efficiency_factor:.2f}, pattern={pattern_match_score:.2f})"
            )
        
        # Return strategy with highest score
        if strategy_scores:
            best_strategy = max(strategy_scores.items(), key=lambda x: x[1])
            logger.info(f"Recommended strategy: {best_strategy[0]} (score={best_strategy[1]:.3f})")
            return best_strategy[0]
        
        return None

    def get_strategy_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive statistics about all strategies.
        
        Returns:
            Dictionary containing strategy statistics
        """
        stats_summary = {}
        
        for strategy, stats in self.strategy_stats.items():
            attempts = stats["attempts"]
            if attempts > 0:
                success_rate = stats["successes"] / attempts
                failure_rate = stats["failures"] / attempts
                avg_duration = stats["total_duration"] / attempts
            else:
                success_rate = 0.0
                failure_rate = 0.0
                avg_duration = 0.0
            
            stats_summary[strategy] = {
                "attempts": attempts,
                "success_rate": success_rate,
                "failure_rate": failure_rate,
                "avg_quality_score": stats["avg_quality_score"],
                "avg_duration": avg_duration,
                "recommendation": self.strategy_recommendations.get(strategy, "neutral"),
            }
        
        return stats_summary

    def identify_patterns(self) -> dict[str, Any]:
        """
        Identify patterns in successful and failed strategy executions.
        
        Returns:
            Dictionary containing identified patterns
        """
        patterns = {
            "success_patterns": {},
            "failure_patterns": {},
            "insights": [],
        }
        
        # Analyze success patterns
        for strategy, records in self.success_patterns.items():
            if len(records) >= 3:  # Need minimum samples
                common_features = self._find_common_features(records)
                patterns["success_patterns"][strategy] = common_features
                
                if common_features:
                    patterns["insights"].append(
                        f"Strategy '{strategy}' succeeds when: {', '.join(common_features)}"
                    )
        
        # Analyze failure patterns
        for strategy, records in self.failure_patterns.items():
            if len(records) >= 3:  # Need minimum samples
                common_features = self._find_common_features(records)
                patterns["failure_patterns"][strategy] = common_features
                
                if common_features:
                    patterns["insights"].append(
                        f"Strategy '{strategy}' fails when: {', '.join(common_features)}"
                    )
        
        return patterns

    def _extract_context_pattern(self, context: dict[str, Any]) -> dict[str, Any]:
        """Extract relevant features from context for pattern matching."""
        pattern = {}
        
        # Extract goal-related features
        if "active_goal" in context:
            goal = context["active_goal"]
            pattern["goal_complexity"] = goal.get("complexity", "unknown")
            pattern["goal_mode"] = goal.get("mode", "unknown")
            pattern["has_parent"] = bool(goal.get("parent_id"))
        
        # Extract system state features
        if "memory" in context:
            pattern["memory_items"] = len(context["memory"].get("recent", []))
        
        # Extract recent action features
        if "recent_actions" in context:
            pattern["recent_action_count"] = len(context["recent_actions"])
        
        return pattern

    def _calculate_pattern_match(
        self, current_pattern: dict[str, Any], historical_patterns: list[dict[str, Any]]
    ) -> float:
        """Calculate how well current pattern matches historical patterns."""
        if not historical_patterns:
            return 0.0
        
        # Take last 10 patterns for comparison
        recent_patterns = historical_patterns[-10:]
        
        match_scores = []
        for hist_pattern in recent_patterns:
            matches = 0
            total = 0
            
            for key in current_pattern:
                if key in hist_pattern:
                    total += 1
                    if current_pattern[key] == hist_pattern[key]:
                        matches += 1
            
            if total > 0:
                match_scores.append(matches / total)
        
        return sum(match_scores) / len(match_scores) if match_scores else 0.0

    def _find_common_features(self, records: list[dict[str, Any]]) -> list[str]:
        """Find common features in a set of execution records."""
        if not records:
            return []
        
        # Count feature occurrences
        feature_counts: dict[str, int] = defaultdict(int)
        
        for record in records:
            pattern = record.get("context_pattern", {})
            for key, value in pattern.items():
                feature = f"{key}={value}"
                feature_counts[feature] += 1
        
        # Return features that appear in >50% of records
        threshold = len(records) * 0.5
        common_features = [
            feature for feature, count in feature_counts.items() if count >= threshold
        ]
        
        return common_features

    def _update_recommendations(self) -> None:
        """Update strategy recommendations based on current statistics."""
        for strategy, stats in self.strategy_stats.items():
            attempts = stats["attempts"]
            
            if attempts < 5:
                # Not enough data
                self.strategy_recommendations[strategy] = "insufficient_data"
                continue
            
            success_rate = stats["successes"] / attempts
            quality = stats["avg_quality_score"]
            
            # Recommend based on performance
            if success_rate >= 0.8 and quality >= 0.7:
                self.strategy_recommendations[strategy] = "highly_recommended"
            elif success_rate >= 0.6 and quality >= 0.5:
                self.strategy_recommendations[strategy] = "recommended"
            elif success_rate >= 0.4:
                self.strategy_recommendations[strategy] = "neutral"
            else:
                self.strategy_recommendations[strategy] = "not_recommended"

    def _load_learning_data(self) -> None:
        """Load persisted learning data from disk."""
        if not self.persistence_path or not self.persistence_path.exists():
            return
        
        try:
            with open(self.persistence_path, "r") as f:
                data = json.load(f)
            
            # Restore strategy stats
            for strategy, stats in data.get("strategy_stats", {}).items():
                self.strategy_stats[strategy] = stats
            
            # Restore patterns
            for strategy, records in data.get("success_patterns", {}).items():
                self.success_patterns[strategy] = records
            
            for strategy, records in data.get("failure_patterns", {}).items():
                self.failure_patterns[strategy] = records
            
            logger.info(f"Loaded learning data from {self.persistence_path}")
        except Exception as e:
            logger.error(f"Failed to load learning data: {e}")

    def save_learning_data(self) -> None:
        """Persist learning data to disk."""
        if not self.persistence_path:
            return
        
        try:
            # Ensure directory exists
            self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare data for serialization
            data = {
                "strategy_stats": dict(self.strategy_stats),
                "success_patterns": dict(self.success_patterns),
                "failure_patterns": dict(self.failure_patterns),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
            
            with open(self.persistence_path, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved learning data to {self.persistence_path}")
        except Exception as e:
            logger.error(f"Failed to save learning data: {e}")

    def reset_learning(self) -> None:
        """Reset all learning data."""
        self.strategy_stats.clear()
        self.success_patterns.clear()
        self.failure_patterns.clear()
        self.strategy_recommendations.clear()
        
        if self.persistence_path and self.persistence_path.exists():
            self.persistence_path.unlink()
        
        logger.info("Learning data reset")
