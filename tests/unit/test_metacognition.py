"""Tests for metacognition."""

import pytest
from datetime import datetime, timedelta
from xagent.core.metacognition import MetaCognitionMonitor


def test_metacognition_initialization():
    """Test metacognition monitor initialization."""
    monitor = MetaCognitionMonitor()
    assert monitor.window_size == 100
    assert len(monitor.performance_history) == 0
    assert len(monitor.error_patterns) == 0
    assert len(monitor.loop_detection) == 0


def test_metacognition_custom_window_size():
    """Test metacognition with custom window size."""
    monitor = MetaCognitionMonitor(window_size=50)
    assert monitor.window_size == 50


def test_evaluate_successful_result():
    """Test evaluating successful result."""
    monitor = MetaCognitionMonitor()

    result = {"success": True, "plan": {"type": "think"}, "error": None}

    evaluation = monitor.evaluate(result)

    assert "timestamp" in evaluation
    assert "success_rate" in evaluation
    assert "efficiency" in evaluation
    assert "issues_detected" in evaluation
    assert "recommendations" in evaluation
    assert len(evaluation["issues_detected"]) == 0


def test_evaluate_failed_result():
    """Test evaluating failed result."""
    monitor = MetaCognitionMonitor()

    result = {"success": False, "plan": {"type": "action"}, "error": "Connection timeout"}

    evaluation = monitor.evaluate(result)

    assert evaluation["success_rate"] == 0.0
    assert "Connection timeout" in monitor.error_patterns


def test_evaluate_repeated_errors():
    """Test detection of repeated errors."""
    monitor = MetaCognitionMonitor()

    # Simulate repeated errors
    for _ in range(5):
        result = {"success": False, "plan": {"type": "action"}, "error": "Same error"}
        evaluation = monitor.evaluate(result)

    # After 5 errors, should detect pattern
    assert monitor.error_patterns["Same error"] == 5
    assert len(evaluation["issues_detected"]) > 0

    # Check if repeated_error is detected
    has_repeated_error = any(
        issue["type"] == "repeated_error" for issue in evaluation["issues_detected"]
    )
    assert has_repeated_error
    assert len(evaluation["recommendations"]) > 0


def test_evaluate_potential_loop():
    """Test detection of potential loops."""
    monitor = MetaCognitionMonitor()

    # Simulate many actions of same type in short time
    for _ in range(15):
        result = {
            "success": True,
            "plan": {"type": "same_action"},
        }
        evaluation = monitor.evaluate(result)

    # Should detect potential loop
    has_loop_detection = any(
        issue["type"] == "potential_loop" for issue in evaluation["issues_detected"]
    )
    assert has_loop_detection

    # Should have recommendations
    assert any("loop" in rec.lower() for rec in evaluation["recommendations"])


def test_success_rate_calculation():
    """Test success rate calculation."""
    monitor = MetaCognitionMonitor()

    # Add 7 successful and 3 failed results
    for i in range(10):
        result = {
            "success": i < 7,  # First 7 are successful
            "plan": {"type": "action"},
        }
        evaluation = monitor.evaluate(result)

    # Success rate should be 0.7
    assert evaluation["success_rate"] == 0.7


def test_efficiency_calculation():
    """Test efficiency calculation."""
    monitor = MetaCognitionMonitor()

    result = {
        "success": True,
        "plan": {"type": "action"},
    }

    evaluation = monitor.evaluate(result)

    # Efficiency should be calculated based on success rate
    assert 0.0 <= evaluation["efficiency"] <= 1.0
    # With 100% success rate, efficiency should be min(1.0 * 1.2, 1.0) = 1.0
    assert evaluation["efficiency"] == 1.0


def test_get_performance_summary_empty():
    """Test performance summary with no history."""
    monitor = MetaCognitionMonitor()

    summary = monitor.get_performance_summary()

    assert summary["total_actions"] == 0
    assert summary["success_rate"] == 0.0
    assert summary["common_errors"] == []


def test_get_performance_summary_with_data():
    """Test performance summary with data."""
    monitor = MetaCognitionMonitor()

    # Add some results
    for i in range(5):
        result = {
            "success": i % 2 == 0,  # Alternating success/failure
            "plan": {"type": "action"},
            "error": f"error_{i % 2}",
        }
        monitor.evaluate(result)

    summary = monitor.get_performance_summary()

    assert summary["total_actions"] == 5
    assert 0.0 <= summary["success_rate"] <= 1.0
    assert len(summary["common_errors"]) > 0


def test_common_errors_sorted():
    """Test that common errors are sorted by frequency."""
    monitor = MetaCognitionMonitor()

    # Add errors with different frequencies
    errors = [
        ("error_a", 5),
        ("error_b", 3),
        ("error_c", 10),
    ]

    for error, count in errors:
        for _ in range(count):
            result = {"success": False, "plan": {"type": "action"}, "error": error}
            monitor.evaluate(result)

    summary = monitor.get_performance_summary()

    # Most common error should be first
    assert summary["common_errors"][0]["error"] == "error_c"
    assert summary["common_errors"][0]["count"] == 10


def test_reset_monitoring():
    """Test reset monitoring."""
    monitor = MetaCognitionMonitor()

    # Add some data
    for i in range(5):
        result = {"success": False, "plan": {"type": "action"}, "error": "test_error"}
        monitor.evaluate(result)

    # Verify data exists
    assert len(monitor.performance_history) > 0
    assert len(monitor.error_patterns) > 0

    # Reset
    monitor.reset_monitoring()

    # Verify data is cleared
    assert len(monitor.performance_history) == 0
    assert len(monitor.error_patterns) == 0
    assert len(monitor.loop_detection) == 0


def test_window_size_limit():
    """Test that performance history respects window size."""
    window_size = 10
    monitor = MetaCognitionMonitor(window_size=window_size)

    # Add more items than window size
    for i in range(20):
        result = {
            "success": True,
            "plan": {"type": "action"},
        }
        monitor.evaluate(result)

    # Should only keep the last window_size items
    assert len(monitor.performance_history) == window_size


def test_evaluation_without_plan():
    """Test evaluation when result has no plan."""
    monitor = MetaCognitionMonitor()

    result = {"success": True, "error": None}

    evaluation = monitor.evaluate(result)

    # Should not crash, should handle gracefully
    assert "success_rate" in evaluation
    assert evaluation["success_rate"] >= 0.0
