"""Tests for OpenTelemetry tracing functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from opentelemetry import trace

from xagent.monitoring.tracing import (
    setup_tracing,
    get_tracer,
    trace_operation,
    add_span_event,
    set_span_attribute,
    TracingHelper,
)


class TestTracingSetup:
    """Test tracing initialization."""

    def test_setup_tracing_basic(self):
        """Test basic tracing setup."""
        # Should not raise
        setup_tracing(service_name="test-service")

        # Should be able to get tracer
        tracer = get_tracer()
        assert tracer is not None

    def test_setup_tracing_with_otlp_endpoint(self):
        """Test tracing setup with OTLP endpoint."""
        with patch("xagent.monitoring.tracing.OTLPSpanExporter"):
            setup_tracing(service_name="test-service", otlp_endpoint="http://localhost:4317")

            tracer = get_tracer()
            assert tracer is not None

    def test_setup_tracing_with_console(self):
        """Test tracing setup with console exporter."""
        setup_tracing(service_name="test-service", enable_console=True)

        tracer = get_tracer()
        assert tracer is not None

    def test_get_tracer_auto_initialize(self):
        """Test that get_tracer auto-initializes if needed."""
        # Get tracer without explicit setup
        tracer = get_tracer()
        assert tracer is not None


class TestTraceOperation:
    """Test trace_operation context manager."""

    def test_trace_operation_basic(self):
        """Test basic operation tracing."""
        setup_tracing(service_name="test")

        with trace_operation("test_operation") as span:
            assert span is not None
            assert span.is_recording()

    def test_trace_operation_with_attributes(self):
        """Test operation tracing with attributes."""
        setup_tracing(service_name="test")

        attributes = {
            "user_id": "123",
            "operation_type": "read",
        }

        with trace_operation("test_operation", attributes) as span:
            assert span is not None

    def test_trace_operation_exception_handling(self):
        """Test that exceptions are recorded in spans."""
        setup_tracing(service_name="test")

        with pytest.raises(ValueError):
            with trace_operation("failing_operation"):
                raise ValueError("Test error")


class TestSpanHelpers:
    """Test span helper functions."""

    def test_add_span_event(self):
        """Test adding events to spans."""
        setup_tracing(service_name="test")

        with trace_operation("test_operation"):
            # Should not raise
            add_span_event("test_event", {"key": "value"})

    def test_set_span_attribute(self):
        """Test setting span attributes."""
        setup_tracing(service_name="test")

        with trace_operation("test_operation"):
            # Should not raise
            set_span_attribute("test_key", "test_value")


class TestTracingHelper:
    """Test TracingHelper convenience methods."""

    def test_trace_cognitive_loop(self):
        """Test cognitive loop tracing."""
        setup_tracing(service_name="test")

        with TracingHelper.trace_cognitive_loop("think"):
            pass

    def test_trace_tool_execution(self):
        """Test tool execution tracing."""
        setup_tracing(service_name="test")

        with TracingHelper.trace_tool_execution("test_tool", {"arg1": "value1"}):
            pass

    def test_trace_memory_operation(self):
        """Test memory operation tracing."""
        setup_tracing(service_name="test")

        with TracingHelper.trace_memory_operation("read", "short_term"):
            pass

    def test_trace_planning(self):
        """Test planning operation tracing."""
        setup_tracing(service_name="test")

        with TracingHelper.trace_planning("llm"):
            pass

    def test_trace_goal_operation(self):
        """Test goal operation tracing."""
        setup_tracing(service_name="test")

        with TracingHelper.trace_goal_operation("create", "goal-123"):
            pass


class TestTracingIntegration:
    """Test tracing integration scenarios."""

    def test_nested_spans(self):
        """Test nested span creation."""
        setup_tracing(service_name="test")

        with trace_operation("parent_operation"):
            with trace_operation("child_operation_1"):
                pass
            with trace_operation("child_operation_2"):
                pass

    def test_concurrent_operations(self):
        """Test that multiple operations can be traced."""
        setup_tracing(service_name="test")

        # Simulate concurrent operations
        with trace_operation("operation_1"):
            pass

        with trace_operation("operation_2"):
            pass

    def test_tracing_with_metrics(self):
        """Test that tracing works alongside metrics."""
        setup_tracing(service_name="test")

        from xagent.monitoring.metrics import get_metrics_collector

        collector = get_metrics_collector()

        with trace_operation("test_operation"):
            # Record some metrics
            collector.record_cognitive_loop(0.5, "success")
