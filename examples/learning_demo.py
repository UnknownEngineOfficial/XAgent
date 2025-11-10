#!/usr/bin/env python
"""
Learning Demo - Demonstrates X-Agent's Emergent Intelligence

This example showcases how X-Agent learns from experience:
- Strategy performance tracking
- Pattern recognition
- Adaptive strategy selection
- Performance improvement over time
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for standalone execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xagent.core.learning import StrategyLearner
from xagent.core.metacognition import MetaCognitionMonitor


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def simulate_strategy_execution(
    learner: StrategyLearner,
    strategy: str,
    context: dict,
    success_rate: float = 0.8,
    quality: float = 0.7,
    duration: float = 1.0,
    num_executions: int = 10,
) -> None:
    """Simulate multiple strategy executions."""
    import random
    
    for i in range(num_executions):
        success = random.random() < success_rate
        actual_quality = quality + random.uniform(-0.1, 0.1)
        actual_duration = duration + random.uniform(-0.2, 0.2)
        
        learner.record_strategy_execution(
            strategy_type=strategy,
            context=context,
            success=success,
            duration=max(0.1, actual_duration),
            quality_score=max(0.0, min(1.0, actual_quality)),
            metadata={"iteration": i + 1},
        )


def main() -> None:
    """Run learning demonstration."""
    
    print_section("X-Agent Learning Demo - Emergent Intelligence")
    
    # Initialize learner
    print("🧠 Initializing Strategy Learner...")
    learner = StrategyLearner()
    print("✓ Learner initialized\n")
    
    # Phase 1: Initial Learning
    print_section("Phase 1: Initial Learning - Different Strategies")
    
    print("Recording executions for 3 different strategies...\n")
    
    # Strategy A: High-performing strategy
    print("Strategy 'decompose': High success (90%), high quality (0.85), fast (1.0s)")
    context_complex = {"active_goal": {"complexity": "high", "mode": "goal_oriented"}}
    simulate_strategy_execution(
        learner, "decompose", context_complex,
        success_rate=0.9, quality=0.85, duration=1.0, num_executions=15
    )
    
    # Strategy B: Medium-performing strategy
    print("Strategy 'direct': Medium success (70%), medium quality (0.6), medium (2.0s)")
    context_simple = {"active_goal": {"complexity": "low", "mode": "goal_oriented"}}
    simulate_strategy_execution(
        learner, "direct", context_simple,
        success_rate=0.7, quality=0.6, duration=2.0, num_executions=15
    )
    
    # Strategy C: Poor-performing strategy
    print("Strategy 'think': Low success (40%), low quality (0.3), slow (3.0s)")
    context_medium = {"active_goal": {"complexity": "medium", "mode": "continuous"}}
    simulate_strategy_execution(
        learner, "think", context_medium,
        success_rate=0.4, quality=0.3, duration=3.0, num_executions=15
    )
    
    print("\n✓ Initial learning phase complete")
    
    # Display statistics
    print_section("Phase 2: Strategy Statistics Analysis")
    
    stats = learner.get_strategy_statistics()
    
    print(f"{'Strategy':<15} {'Attempts':<10} {'Success Rate':<15} {'Avg Quality':<15} {'Recommendation':<20}")
    print("-" * 75)
    
    for strategy, stat in sorted(stats.items(), key=lambda x: x[1]['success_rate'], reverse=True):
        print(
            f"{strategy:<15} "
            f"{stat['attempts']:<10} "
            f"{stat['success_rate']:.1%}{'':>6} "
            f"{stat['avg_quality_score']:.2f}{'':>9} "
            f"{stat['recommendation']:<20}"
        )
    
    # Get best strategy recommendation
    print_section("Phase 3: Intelligent Strategy Selection")
    
    test_contexts = [
        {"active_goal": {"complexity": "high", "mode": "goal_oriented"}},
        {"active_goal": {"complexity": "low", "mode": "goal_oriented"}},
        {"active_goal": {"complexity": "medium", "mode": "continuous"}},
    ]
    
    print("Testing strategy recommendations for different contexts:\n")
    
    for i, context in enumerate(test_contexts, 1):
        recommended = learner.get_best_strategy(context)
        goal_info = context["active_goal"]
        print(
            f"{i}. Context: complexity={goal_info['complexity']}, mode={goal_info['mode']}\n"
            f"   → Recommended Strategy: {recommended}\n"
        )
    
    # Pattern identification
    print_section("Phase 4: Pattern Recognition")
    
    patterns = learner.identify_patterns()
    
    print("Success Patterns Identified:")
    for strategy, features in patterns["success_patterns"].items():
        if features:
            print(f"  • {strategy}: {', '.join(features)}")
    
    print("\nFailure Patterns Identified:")
    for strategy, features in patterns["failure_patterns"].items():
        if features:
            print(f"  • {strategy}: {', '.join(features)}")
    
    if patterns["insights"]:
        print("\nKey Insights:")
        for insight in patterns["insights"]:
            print(f"  💡 {insight}")
    
    # Integration with Metacognition
    print_section("Phase 5: Metacognition Integration")
    
    print("Creating metacognition monitor with learning enabled...")
    monitor = MetaCognitionMonitor(enable_learning=True)
    
    # Simulate some executions
    print("\nSimulating agent executions with metacognition...\n")
    
    for i in range(5):
        context = {"active_goal": {"complexity": "high"}}
        result = {
            "success": True,
            "plan": {"type": "decompose"},
            "quality_score": 0.85,
            "duration": 1.0,
        }
        evaluation = monitor.evaluate(result, context=context)
        print(f"  Iteration {i+1}: Success rate = {evaluation['success_rate']:.1%}")
    
    # Get learning insights from monitor
    print("\n📊 Learning Insights from Metacognition:")
    insights = monitor.get_learning_insights()
    
    if insights["learning_enabled"]:
        print(f"  ✓ Learning is active")
        print(f"  ✓ {len(insights['strategy_statistics'])} strategies tracked")
        
        # Get recommendation from metacognition
        context = {"active_goal": {"complexity": "high"}}
        recommended = monitor.get_strategy_recommendation(context)
        print(f"  ✓ Recommended strategy for high complexity: {recommended}")
    
    # Persistence demonstration
    print_section("Phase 6: Learning Persistence")
    
    import tempfile
    temp_dir = tempfile.mkdtemp()
    persistence_path = Path(temp_dir) / "learning_data.json"
    
    print(f"Saving learning data to: {persistence_path}")
    
    # Create new learner with persistence
    persistent_learner = StrategyLearner(persistence_path=str(persistence_path))
    
    # Record some data
    context = {"active_goal": {"complexity": "high"}}
    for _ in range(5):
        persistent_learner.record_strategy_execution(
            "decompose", context, success=True, quality_score=0.9
        )
    
    # Save
    persistent_learner.save_learning_data()
    print("✓ Learning data saved")
    
    # Load in new instance
    print("\nLoading learning data in new learner instance...")
    loaded_learner = StrategyLearner(persistence_path=str(persistence_path))
    
    loaded_stats = loaded_learner.get_strategy_statistics()
    if "decompose" in loaded_stats:
        print(f"✓ Successfully loaded: {loaded_stats['decompose']['attempts']} recorded attempts")
    
    # Summary
    print_section("Summary: Emergent Intelligence Capabilities")
    
    print("✅ Strategy Performance Tracking")
    print("   - Tracks success rate, quality, and efficiency per strategy")
    print("   - Maintains history of executions with context")
    print()
    
    print("✅ Pattern Recognition")
    print("   - Identifies common features in successful/failed executions")
    print("   - Learns which strategies work best in which contexts")
    print()
    
    print("✅ Adaptive Strategy Selection")
    print("   - Recommends best strategy based on learned patterns")
    print("   - Considers success rate, quality, efficiency, and context")
    print()
    
    print("✅ Continuous Improvement")
    print("   - Performance improves over time with more executions")
    print("   - Automatic strategy ranking and recommendations")
    print()
    
    print("✅ Learning Persistence")
    print("   - Save/load learning data across sessions")
    print("   - Accumulated knowledge retained")
    print()
    
    print("🎯 Result: X-Agent demonstrates true emergent intelligence!")
    print("   The agent learns from experience and continuously improves its")
    print("   decision-making without explicit programming for each scenario.")
    print()


if __name__ == "__main__":
    main()
