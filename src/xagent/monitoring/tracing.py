"""OpenTelemetry distributed tracing for X-Agent.

Provides comprehensive tracing capabilities for debugging and performance analysis
across the agent, API, tools, and memory operations.
"""

from typing import Optional, Dict, Any
from contextlib import contextmanager
import os

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from xagent.utils.logging import get_logger

logger = get_logger(__name__)


# Global tracer provider
_tracer_provider: Optional[TracerProvider] = None
_tracer: Optional[trace.Tracer] = None


def setup_tracing(
    service_name: str = "x-agent",
    otlp_endpoint: Optional[str] = None,
    enable_console: bool = False,
) -> None:
    """
    Initialize OpenTelemetry tracing.
    
    Args:
        service_name: Name of the service for tracing
        otlp_endpoint: OTLP collector endpoint (e.g., "http://localhost:4317")
        enable_console: Whether to enable console exporter for debugging
    """
    global _tracer_provider, _tracer
    
    # Create resource with service info
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "0.1.0",
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })
    
    # Create tracer provider
    _tracer_provider = TracerProvider(resource=resource)
    
    # Add exporters
    if otlp_endpoint:
        # OTLP exporter for production
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info(f"OpenTelemetry OTLP exporter configured: {otlp_endpoint}")
    
    if enable_console:
        # Console exporter for debugging
        console_exporter = ConsoleSpanExporter()
        _tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
        logger.info("OpenTelemetry console exporter enabled")
    
    # Set as global tracer provider
    trace.set_tracer_provider(_tracer_provider)
    
    # Get tracer
    _tracer = trace.get_tracer(__name__)
    
    logger.info(f"OpenTelemetry tracing initialized for service: {service_name}")


def get_tracer() -> trace.Tracer:
    """
    Get the global tracer.
    
    Returns:
        OpenTelemetry tracer
        
    Raises:
        RuntimeError: If tracing hasn't been initialized
    """
    if _tracer is None:
        # Auto-initialize with defaults if not already done
        setup_tracing()
    
    return _tracer  # type: ignore


def instrument_fastapi(app) -> None:
    """
    Instrument FastAPI application with automatic tracing.
    
    Args:
        app: FastAPI application instance
    """
    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumented with OpenTelemetry")
    except Exception as e:
        logger.warning(f"Failed to instrument FastAPI: {e}")


@contextmanager
def trace_operation(
    operation_name: str,
    attributes: Optional[Dict[str, Any]] = None,
):
    """
    Context manager for tracing operations.
    
    Args:
        operation_name: Name of the operation
        attributes: Additional attributes to add to the span
        
    Example:
        with trace_operation("cognitive_loop.think", {"goal_id": goal.id}):
            # ... thinking logic ...
    """
    tracer = get_tracer()
    
    with tracer.start_as_current_span(operation_name) as span:
        # Add attributes
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        
        try:
            yield span
        except Exception as e:
            # Record exception in span
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise


def add_span_event(event_name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """
    Add an event to the current span.
    
    Args:
        event_name: Name of the event
        attributes: Event attributes
    """
    current_span = trace.get_current_span()
    if current_span.is_recording():
        current_span.add_event(event_name, attributes or {})


def set_span_attribute(key: str, value: Any) -> None:
    """
    Set an attribute on the current span.
    
    Args:
        key: Attribute key
        value: Attribute value
    """
    current_span = trace.get_current_span()
    if current_span.is_recording():
        current_span.set_attribute(key, str(value))


class TracingHelper:
    """Helper class for common tracing operations."""
    
    @staticmethod
    def trace_cognitive_loop(phase: str):
        """Trace a cognitive loop phase."""
        return trace_operation(f"cognitive_loop.{phase}")
    
    @staticmethod
    def trace_tool_execution(tool_name: str, tool_args: Optional[Dict[str, Any]] = None):
        """Trace tool execution."""
        attributes = {"tool.name": tool_name}
        if tool_args:
            # Add sanitized tool arguments
            attributes.update({
                f"tool.arg.{k}": str(v)[:100]  # Limit to 100 chars
                for k, v in tool_args.items()
            })
        return trace_operation(f"tool.execute.{tool_name}", attributes)
    
    @staticmethod
    def trace_memory_operation(operation: str, memory_type: str):
        """Trace memory operations."""
        return trace_operation(
            f"memory.{operation}",
            {"memory.type": memory_type}
        )
    
    @staticmethod
    def trace_planning(strategy: str):
        """Trace planning operations."""
        return trace_operation(
            "planner.plan",
            {"planning.strategy": strategy}
        )
    
    @staticmethod
    def trace_goal_operation(operation: str, goal_id: Optional[str] = None):
        """Trace goal-related operations."""
        attributes = {}
        if goal_id:
            attributes["goal.id"] = goal_id
        return trace_operation(f"goal.{operation}", attributes)


# Convenience instance
tracing = TracingHelper()
