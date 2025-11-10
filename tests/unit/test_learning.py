"""Tests for learning module."""

import json
import tempfile
from pathlib import Path

import pytest

from xagent.core.learning import StrategyLearner


class TestStrategyLearner:
    """Test StrategyLearner class."""

    def test_initialization(self) -> None:
        """Test learner initialization."""
        learner = StrategyLearner()
        assert learner.strategy_stats is not None
        assert learner.success_patterns is not None
        assert learner.failure_patterns is not None

    def test_record_strategy_execution_success(self) -> None:
        """Test recording successful strategy execution."""
        learner = StrategyLearner()
        
        context = {
            "active_goal": {
                "complexity": "high",
                "mode": "goal_oriented",
                "parent_id": None,
            }
        }
        
        learner.record_strategy_execution(
            strategy_type="decompose",
            context=context,
            success=True,
            duration=1.5,
            quality_score=0.8,
        )
        
        stats = learner.strategy_stats["decompose"]
        assert stats["attempts"] == 1
        assert stats["successes"] == 1
        assert stats["failures"] == 0
        assert stats["total_duration"] == 1.5
        assert stats["avg_quality_score"] == 0.8

    def test_record_strategy_execution_failure(self) -> None:
        """Test recording failed strategy execution."""
        learner = StrategyLearner()
        
        context = {"active_goal": {"complexity": "low"}}
        
        learner.record_strategy_execution(
            strategy_type="direct",
            context=context,
            success=False,
            duration=0.5,
            quality_score=0.2,
        )
        
        stats = learner.strategy_stats["direct"]
        assert stats["attempts"] == 1
        assert stats["successes"] == 0
        assert stats["failures"] == 1

    def test_record_multiple_executions(self) -> None:
        """Test recording multiple strategy executions."""
        learner = StrategyLearner()
        
        context = {"active_goal": {"complexity": "medium"}}
        
        # Record 5 successes and 2 failures
        for _ in range(5):
            learner.record_strategy_execution(
                "think", context, success=True, quality_score=0.7
            )
        
        for _ in range(2):
            learner.record_strategy_execution(
                "think", context, success=False, quality_score=0.3
            )
        
        stats = learner.strategy_stats["think"]
        assert stats["attempts"] == 7
        assert stats["successes"] == 5
        assert stats["failures"] == 2

    def test_get_best_strategy_no_data(self) -> None:
        """Test get_best_strategy with no data."""
        learner = StrategyLearner()
        
        result = learner.get_best_strategy({"active_goal": {}})
        assert result is None

    def test_get_best_strategy_with_data(self) -> None:
        """Test get_best_strategy with historical data."""
        learner = StrategyLearner()
        
        context = {"active_goal": {"complexity": "high"}}
        
        # Record good performance for "decompose"
        for _ in range(10):
            learner.record_strategy_execution(
                "decompose", context, success=True, quality_score=0.9, duration=1.0
            )
        
        # Record poor performance for "direct"
        for _ in range(10):
            learner.record_strategy_execution(
                "direct", context, success=False, quality_score=0.2, duration=5.0
            )
        
        best = learner.get_best_strategy(context)
        assert best == "decompose"

    def test_get_best_strategy_with_filter(self) -> None:
        """Test get_best_strategy with available strategies filter."""
        learner = StrategyLearner()
        
        context = {"active_goal": {}}
        
        # Record data for multiple strategies
        learner.record_strategy_execution(
            "decompose", context, success=True, quality_score=0.9
        )
        learner.record_strategy_execution(
            "direct", context, success=True, quality_score=0.7
        )
        learner.record_strategy_execution(
            "think", context, success=True, quality_score=0.5
        )
        
        # Only allow "direct" and "think"
        best = learner.get_best_strategy(context, available_strategies=["direct", "think"])
        assert best in ["direct", "think"]

    def test_get_strategy_statistics(self) -> None:
        """Test get_strategy_statistics."""
        learner = StrategyLearner()
        
        context = {"active_goal": {}}
        
        # Record some executions
        for _ in range(8):
            learner.record_strategy_execution(
                "decompose", context, success=True, quality_score=0.8, duration=1.0
            )
        
        for _ in range(2):
            learner.record_strategy_execution(
                "decompose", context, success=False, quality_score=0.3, duration=2.0
            )
        
        stats = learner.get_strategy_statistics()
        
        assert "decompose" in stats
        decompose_stats = stats["decompose"]
        assert decompose_stats["attempts"] == 10
        assert decompose_stats["success_rate"] == 0.8
        assert decompose_stats["failure_rate"] == 0.2
        assert decompose_stats["avg_duration"] == 1.2
        assert "recommendation" in decompose_stats

    def test_identify_patterns_insufficient_data(self) -> None:
        """Test identify_patterns with insufficient data."""
        learner = StrategyLearner()
        
        # Only 2 records (need 3+)
        context = {"active_goal": {"complexity": "high"}}
        learner.record_strategy_execution("decompose", context, success=True)
        learner.record_strategy_execution("decompose", context, success=True)
        
        patterns = learner.identify_patterns()
        
        assert "success_patterns" in patterns
        assert "failure_patterns" in patterns
        assert "insights" in patterns
        # Not enough data for patterns
        assert len(patterns["success_patterns"]) == 0

    def test_identify_patterns_with_data(self) -> None:
        """Test identify_patterns with sufficient data."""
        learner = StrategyLearner()
        
        # Record multiple successes with same pattern
        context = {"active_goal": {"complexity": "high", "mode": "goal_oriented"}}
        for _ in range(5):
            learner.record_strategy_execution("decompose", context, success=True)
        
        patterns = learner.identify_patterns()
        
        assert "success_patterns" in patterns
        if "decompose" in patterns["success_patterns"]:
            assert len(patterns["success_patterns"]["decompose"]) > 0

    def test_extract_context_pattern(self) -> None:
        """Test context pattern extraction."""
        learner = StrategyLearner()
        
        context = {
            "active_goal": {
                "complexity": "high",
                "mode": "continuous",
                "parent_id": "parent_123",
            },
            "memory": {"recent": [1, 2, 3]},
            "recent_actions": [{"action": "think"}],
        }
        
        pattern = learner._extract_context_pattern(context)
        
        assert pattern["goal_complexity"] == "high"
        assert pattern["goal_mode"] == "continuous"
        assert pattern["has_parent"] is True
        assert pattern["memory_items"] == 3
        assert pattern["recent_action_count"] == 1

    def test_calculate_pattern_match(self) -> None:
        """Test pattern matching calculation."""
        learner = StrategyLearner()
        
        current = {"goal_complexity": "high", "goal_mode": "goal_oriented"}
        historical = [
            {"goal_complexity": "high", "goal_mode": "goal_oriented"},
            {"goal_complexity": "high", "goal_mode": "continuous"},
            {"goal_complexity": "low", "goal_mode": "goal_oriented"},
        ]
        
        score = learner._calculate_pattern_match(current, historical)
        
        assert 0.0 <= score <= 1.0
        assert score > 0.0  # Should have some matches

    def test_update_recommendations(self) -> None:
        """Test recommendation updates."""
        learner = StrategyLearner()
        
        context = {"active_goal": {}}
        
        # Record high-performing strategy
        for _ in range(10):
            learner.record_strategy_execution(
                "decompose", context, success=True, quality_score=0.9
            )
        
        # Record low-performing strategy
        for _ in range(10):
            learner.record_strategy_execution(
                "direct", context, success=False, quality_score=0.2
            )
        
        assert learner.strategy_recommendations["decompose"] == "highly_recommended"
        assert learner.strategy_recommendations["direct"] == "not_recommended"

    def test_persistence(self) -> None:
        """Test saving and loading learning data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence_path = Path(tmpdir) / "learning_data.json"
            
            # Create learner and record some data
            learner1 = StrategyLearner(persistence_path=str(persistence_path))
            context = {"active_goal": {"complexity": "high"}}
            
            for _ in range(5):
                learner1.record_strategy_execution(
                    "decompose", context, success=True, quality_score=0.8
                )
            
            # Save data
            learner1.save_learning_data()
            
            # Create new learner and load data
            learner2 = StrategyLearner(persistence_path=str(persistence_path))
            
            # Check data was loaded
            stats = learner2.strategy_stats["decompose"]
            assert stats["attempts"] == 5
            assert stats["successes"] == 5

    def test_reset_learning(self) -> None:
        """Test resetting learning data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence_path = Path(tmpdir) / "learning_data.json"
            learner = StrategyLearner(persistence_path=str(persistence_path))
            
            # Record some data
            context = {"active_goal": {}}
            learner.record_strategy_execution("think", context, success=True)
            learner.save_learning_data()
            
            # Reset
            learner.reset_learning()
            
            # Check data is cleared
            assert len(learner.strategy_stats) == 0
            assert len(learner.success_patterns) == 0
            assert not persistence_path.exists()

    def test_average_quality_score_update(self) -> None:
        """Test that average quality score is updated correctly."""
        learner = StrategyLearner()
        context = {"active_goal": {}}
        
        # First execution with quality 0.8
        learner.record_strategy_execution(
            "think", context, success=True, quality_score=0.8
        )
        assert learner.strategy_stats["think"]["avg_quality_score"] == 0.8
        
        # Second execution with quality 0.6
        learner.record_strategy_execution(
            "think", context, success=True, quality_score=0.6
        )
        # Average should be (0.8 + 0.6) / 2 = 0.7
        assert abs(learner.strategy_stats["think"]["avg_quality_score"] - 0.7) < 0.001

    def test_find_common_features(self) -> None:
        """Test finding common features in records."""
        learner = StrategyLearner()
        
        records = [
            {"context_pattern": {"goal_complexity": "high", "goal_mode": "goal_oriented"}},
            {"context_pattern": {"goal_complexity": "high", "goal_mode": "continuous"}},
            {"context_pattern": {"goal_complexity": "high", "goal_mode": "goal_oriented"}},
        ]
        
        common = learner._find_common_features(records)
        
        # "goal_complexity=high" should appear in all (100%)
        assert "goal_complexity=high" in common

    def test_insufficient_data_recommendation(self) -> None:
        """Test recommendation with insufficient data."""
        learner = StrategyLearner()
        context = {"active_goal": {}}
        
        # Only 3 executions (need 5+)
        for _ in range(3):
            learner.record_strategy_execution(
                "think", context, success=True, quality_score=0.9
            )
        
        assert learner.strategy_recommendations["think"] == "insufficient_data"


class TestStrategyLearnerEdgeCases:
    """Test edge cases for StrategyLearner."""

    def test_empty_context(self) -> None:
        """Test with empty context."""
        learner = StrategyLearner()
        
        learner.record_strategy_execution(
            "think", context={}, success=True, quality_score=0.5
        )
        
        stats = learner.strategy_stats["think"]
        assert stats["attempts"] == 1

    def test_get_best_strategy_empty_available_list(self) -> None:
        """Test get_best_strategy with empty available strategies list."""
        learner = StrategyLearner()
        context = {"active_goal": {}}
        
        learner.record_strategy_execution("think", context, success=True)
        
        result = learner.get_best_strategy(context, available_strategies=[])
        assert result is None

    def test_pattern_match_with_empty_historical(self) -> None:
        """Test pattern matching with empty historical data."""
        learner = StrategyLearner()
        
        current = {"goal_complexity": "high"}
        score = learner._calculate_pattern_match(current, [])
        
        assert score == 0.0

    def test_persistence_with_no_path(self) -> None:
        """Test persistence operations with no path set."""
        learner = StrategyLearner()  # No persistence path
        
        # Should not raise errors
        learner.save_learning_data()
        learner._load_learning_data()

    def test_load_corrupted_data(self) -> None:
        """Test loading corrupted persistence data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence_path = Path(tmpdir) / "learning_data.json"
            
            # Write invalid JSON
            with open(persistence_path, "w") as f:
                f.write("not valid json{{{")
            
            # Should not crash, just log error
            learner = StrategyLearner(persistence_path=str(persistence_path))
            
            # Should have empty stats
            assert len(learner.strategy_stats) == 0

    def test_multiple_strategies_comparison(self) -> None:
        """Test comparing multiple strategies with different performance."""
        learner = StrategyLearner()
        context = {"active_goal": {"complexity": "high"}}
        
        # Strategy A: High success, high quality, fast
        for _ in range(10):
            learner.record_strategy_execution(
                "strategy_a", context, success=True, quality_score=0.9, duration=1.0
            )
        
        # Strategy B: Medium success, medium quality, slow
        for _ in range(10):
            learner.record_strategy_execution(
                "strategy_b", context, success=True, quality_score=0.6, duration=5.0
            )
        for _ in range(5):
            learner.record_strategy_execution(
                "strategy_b", context, success=False, quality_score=0.3, duration=5.0
            )
        
        # Strategy C: Low success, low quality
        for _ in range(10):
            learner.record_strategy_execution(
                "strategy_c", context, success=False, quality_score=0.2, duration=2.0
            )
        
        best = learner.get_best_strategy(context)
        assert best == "strategy_a"
