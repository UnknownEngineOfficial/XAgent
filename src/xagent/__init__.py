"""X-Agent: Autonomous AI Agent System"""

__version__ = "0.1.0"
__author__ = "XTeam"
__description__ = "Autonomous X-Agent: Self-thinking, decision-making AI agent"

# Lazy imports to avoid dependency issues
__all__ = [
    "XAgent",
    "CognitiveLoop",
    "GoalEngine",
]


def __getattr__(name):
    """Lazy import to avoid loading all dependencies at once."""
    if name == "XAgent":
        from xagent.core.agent import XAgent
        return XAgent
    elif name == "CognitiveLoop":
        from xagent.core.cognitive_loop import CognitiveLoop
        return CognitiveLoop
    elif name == "GoalEngine":
        from xagent.core.goal_engine import GoalEngine
        return GoalEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

