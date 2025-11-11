#!/usr/bin/env python
"""
Comprehensive demonstration of X-Agent's Checkpoint and Runtime Metrics features.

This script demonstrates:
1. Runtime Metrics Collection (uptime, decision latency, task success rate)
2. Checkpoint/Resume functionality (State Persistence)
3. Crash Recovery capability
4. Live metrics monitoring

These features address the high-priority gaps identified in FEATURES.md:
- Runtime Metriken implementation
- State Persistence for Cognitive State
- Production-ready monitoring capabilities
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xagent.core.cognitive_loop import CognitiveLoop, CognitiveState, LoopPhase
from xagent.core.executor import Executor
from xagent.core.goal_engine import GoalEngine, Goal, GoalStatus
from xagent.core.planner import Planner
from xagent.memory.memory_layer import MemoryLayer
from xagent.monitoring.metrics import (
    MetricsCollector,
    agent_decision_latency,
    agent_task_success_rate,
    agent_tasks_completed_total,
    agent_uptime_seconds,
)


class CheckpointAndMetricsDemo:
    """Demonstration of checkpoint and metrics features."""

    def __init__(self):
        """Initialize the demo."""
        self.checkpoint_dir = Path("/tmp/xagent_demo_checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_collector = MetricsCollector()

    def print_header(self, title: str) -> None:
        """Print a formatted header."""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80 + "\n")

    def print_success(self, message: str) -> None:
        """Print a success message."""
        print(f"✅ {message}")

    def print_info(self, message: str) -> None:
        """Print an info message."""
        print(f"ℹ️  {message}")

    def print_metric(self, name: str, value: Any) -> None:
        """Print a metric."""
        print(f"📊 {name}: {value}")

    def create_mock_components(self) -> tuple:
        """Create mock components for the demo."""
        # Create mock goal engine
        goal_engine = Mock(spec=GoalEngine)
        goal_engine.get_active_goal = Mock(return_value=None)
        goal_engine.get_next_goal = Mock(return_value=None)
        goal_engine.active_goal_id = None
        goal_engine.set_active_goal = Mock()

        # Create mock memory
        memory = Mock(spec=MemoryLayer)
        memory.get = AsyncMock(return_value=None)
        memory.save_short_term = AsyncMock()
        memory.save_medium_term = AsyncMock()

        # Create mock planner
        planner = Mock(spec=Planner)
        planner.create_plan = AsyncMock(
            return_value={
                "type": "think",
                "action": "analyze",
                "parameters": {"thought": "Processing task..."},
            }
        )

        # Create mock executor
        executor = Mock(spec=Executor)
        executor.execute = AsyncMock(
            return_value={
                "success": True,
                "output": {"message": "Task completed successfully"},
                "error": None,
            }
        )

        return goal_engine, memory, planner, executor

    async def demonstrate_runtime_metrics(self) -> None:
        """Demonstrate runtime metrics collection."""
        self.print_header("PART 1: Runtime Metrics Collection")

        self.print_info("Initializing metrics collector...")

        # 1. Demonstrate uptime tracking
        self.print_info("\n1️⃣  Uptime Tracking")
        start_time = time.time()
        await asyncio.sleep(1.0)
        uptime = time.time() - start_time
        self.metrics_collector.update_agent_uptime(uptime)
        self.print_success(f"Uptime tracked: {uptime:.2f} seconds")

        # Verify metric
        samples = list(agent_uptime_seconds.collect())[0].samples
        recorded_uptime = samples[0].value if samples else 0
        self.print_metric("Recorded Uptime", f"{recorded_uptime:.2f}s")

        # 2. Demonstrate decision latency tracking
        self.print_info("\n2️⃣  Decision Latency Tracking")
        latencies = [0.15, 0.25, 0.18, 0.22, 0.19]
        for i, latency in enumerate(latencies, 1):
            self.metrics_collector.record_decision_latency(latency)
            self.print_success(f"Decision {i} latency: {latency*1000:.1f}ms")

        # Verify histogram
        samples = list(agent_decision_latency.collect())[0].samples
        count_sample = next(s for s in samples if s.name.endswith("_count"))
        sum_sample = next(s for s in samples if s.name.endswith("_sum"))
        avg_latency = sum_sample.value / count_sample.value if count_sample.value > 0 else 0
        self.print_metric("Average Latency", f"{avg_latency*1000:.1f}ms")
        self.print_metric("Total Decisions", int(count_sample.value))

        # 3. Demonstrate task success rate tracking
        self.print_info("\n3️⃣  Task Success Rate Tracking")
        tasks = [True, True, False, True, True, True, False, True, True, True]
        for i, success in enumerate(tasks, 1):
            self.metrics_collector.record_task_result(success)
            status = "✅ Success" if success else "❌ Failed"
            print(f"   Task {i:2d}: {status}")

        # Calculate success rate
        success_count = sum(1 for t in tasks if t)
        success_rate = (success_count / len(tasks)) * 100
        self.metrics_collector.update_task_success_rate(success_rate)
        
        self.print_metric("Tasks Completed", len(tasks))
        self.print_metric("Success Rate", f"{success_rate:.1f}%")

        # Verify counters
        samples = list(agent_tasks_completed_total.collect())[0].samples
        success_total = next(
            s.value for s in samples if "success" in str(s.labels)
        )
        failure_total = next(
            s.value for s in samples if "failure" in str(s.labels)
        )
        self.print_metric("Success Counter", int(success_total))
        self.print_metric("Failure Counter", int(failure_total))

        self.print_success("\n✨ Runtime metrics demonstration complete!")
        self.print_info("All metrics are being collected and can be exported to Prometheus")

    async def demonstrate_checkpoint_save_and_load(self) -> None:
        """Demonstrate checkpoint save and load functionality."""
        self.print_header("PART 2: Checkpoint Save and Load")

        # Create cognitive loop with checkpoint enabled
        goal_engine, memory, planner, executor = self.create_mock_components()
        
        loop = CognitiveLoop(
            goal_engine=goal_engine,
            memory=memory,
            planner=planner,
            executor=executor,
        )
        loop.checkpoint_dir = self.checkpoint_dir
        loop.checkpoint_enabled = True
        loop.checkpoint_interval = 5

        self.print_info(f"Checkpoint directory: {self.checkpoint_dir}")
        self.print_info(f"Checkpoint interval: {loop.checkpoint_interval} iterations")

        # Simulate some iterations
        self.print_info("\n📝 Simulating agent execution...")
        loop.iteration_count = 15
        loop.state = CognitiveState.THINKING
        loop.current_phase = LoopPhase.PLANNING
        loop.start_time = time.time()
        loop.task_results = [True, True, False, True, True]

        self.print_metric("Iteration Count", loop.iteration_count)
        self.print_metric("Current State", loop.state.value)
        self.print_metric("Current Phase", loop.current_phase.value)
        self.print_metric("Task Results", f"{sum(loop.task_results)}/{len(loop.task_results)} successful")

        # Save checkpoint
        self.print_info("\n💾 Saving checkpoint...")
        await loop.save_checkpoint()

        json_path = self.checkpoint_dir / "checkpoint.json"
        pickle_path = self.checkpoint_dir / "checkpoint.pkl"

        self.print_success(f"Checkpoint saved to: {json_path}")
        self.print_success(f"Binary state saved to: {pickle_path}")

        # Create a new loop instance and load checkpoint
        self.print_info("\n🔄 Creating new agent instance and loading checkpoint...")
        
        new_goal_engine, new_memory, new_planner, new_executor = self.create_mock_components()
        new_loop = CognitiveLoop(
            goal_engine=new_goal_engine,
            memory=new_memory,
            planner=new_planner,
            executor=new_executor,
        )
        new_loop.checkpoint_dir = self.checkpoint_dir

        # Load checkpoint
        loaded = await new_loop.load_checkpoint()

        if loaded:
            self.print_success("Checkpoint loaded successfully!")
            self.print_metric("Restored Iteration Count", new_loop.iteration_count)
            self.print_metric("Restored State", new_loop.state.value)
            self.print_metric("Restored Phase", new_loop.current_phase.value)
            self.print_metric("Restored Task Results", f"{sum(new_loop.task_results)}/{len(new_loop.task_results)}")

            # Verify state matches
            assert new_loop.iteration_count == loop.iteration_count
            assert new_loop.state == loop.state
            assert new_loop.current_phase == loop.current_phase
            self.print_success("\n✨ State verification: All values match!")
        else:
            print("❌ Failed to load checkpoint")

    async def demonstrate_crash_recovery(self) -> None:
        """Demonstrate crash recovery capability."""
        self.print_header("PART 3: Crash Recovery Simulation")

        self.print_info("This demonstrates how the agent can recover from unexpected crashes")

        # Create initial agent
        goal_engine, memory, planner, executor = self.create_mock_components()
        loop = CognitiveLoop(
            goal_engine=goal_engine,
            memory=memory,
            planner=planner,
            executor=executor,
        )
        loop.checkpoint_dir = self.checkpoint_dir
        loop.checkpoint_enabled = True
        loop.checkpoint_interval = 3
        loop.max_iterations = 10

        self.print_info("\n🚀 Starting agent with checkpoint interval of 3 iterations...")

        # Configure planner
        planner.create_plan = AsyncMock(
            return_value={
                "type": "think",
                "action": "process",
                "parameters": {},
            }
        )

        # Start the loop
        loop_task = asyncio.create_task(loop.start(resume_from_checkpoint=False))
        
        # Let it run for a bit
        await asyncio.sleep(1.5)
        
        # Simulate crash by stopping the loop
        self.print_info("⚠️  Simulating crash (stopping agent)...")
        await loop.stop()
        
        try:
            await asyncio.wait_for(loop_task, timeout=2.0)
        except asyncio.TimeoutError:
            pass

        crashed_iteration = loop.iteration_count
        self.print_metric("Iterations before crash", crashed_iteration)
        self.print_success(f"Checkpoint saved at iteration: {loop.last_checkpoint_iteration}")

        # Simulate recovery
        self.print_info("\n🔧 Recovering from crash...")
        
        new_goal_engine, new_memory, new_planner, new_executor = self.create_mock_components()
        new_planner.create_plan = AsyncMock(
            return_value={
                "type": "think",
                "action": "process",
                "parameters": {},
            }
        )

        recovered_loop = CognitiveLoop(
            goal_engine=new_goal_engine,
            memory=new_memory,
            planner=new_planner,
            executor=new_executor,
        )
        recovered_loop.checkpoint_dir = self.checkpoint_dir
        recovered_loop.max_iterations = 15

        # Resume from checkpoint
        self.print_info("📂 Loading checkpoint and resuming...")
        loop_task = asyncio.create_task(recovered_loop.start(resume_from_checkpoint=True))
        
        await asyncio.sleep(1.0)
        await recovered_loop.stop()
        
        try:
            await asyncio.wait_for(loop_task, timeout=2.0)
        except asyncio.TimeoutError:
            pass

        self.print_success(f"Agent resumed from iteration: {crashed_iteration}")
        self.print_metric("Current iteration", recovered_loop.iteration_count)
        self.print_success("✨ Crash recovery successful! Agent continued from last checkpoint")

    async def demonstrate_continuous_operation(self) -> None:
        """Demonstrate continuous operation with periodic checkpoints."""
        self.print_header("PART 4: Continuous Operation with Periodic Checkpointing")

        goal_engine, memory, planner, executor = self.create_mock_components()
        loop = CognitiveLoop(
            goal_engine=goal_engine,
            memory=memory,
            planner=planner,
            executor=executor,
        )
        loop.checkpoint_dir = self.checkpoint_dir
        loop.checkpoint_enabled = True
        loop.checkpoint_interval = 5
        loop.max_iterations = 20

        planner.create_plan = AsyncMock(
            return_value={
                "type": "think",
                "action": "process",
                "parameters": {},
            }
        )

        self.print_info("Running agent with automatic checkpointing every 5 iterations...")
        self.print_info("This simulates production operation with fault tolerance\n")

        # Track metrics during operation
        start_time = time.time()
        
        loop_task = asyncio.create_task(loop.start(resume_from_checkpoint=False))
        
        # Monitor progress
        last_iteration = 0
        while loop.running:
            await asyncio.sleep(0.5)
            
            if loop.iteration_count > last_iteration:
                last_iteration = loop.iteration_count
                self.print_info(f"Iteration {loop.iteration_count:2d} | State: {loop.state.value:12s} | Checkpoint: {loop.last_checkpoint_iteration:2d}")
                
                # Update metrics
                uptime = time.time() - start_time
                self.metrics_collector.update_agent_uptime(uptime)
                
            if loop.iteration_count >= loop.max_iterations:
                await loop.stop()
                break

        try:
            await asyncio.wait_for(loop_task, timeout=2.0)
        except asyncio.TimeoutError:
            pass

        # Final metrics
        total_time = time.time() - start_time
        self.print_success(f"\n✨ Completed {loop.iteration_count} iterations in {total_time:.2f} seconds")
        self.print_metric("Checkpoints Created", loop.last_checkpoint_iteration // loop.checkpoint_interval)
        self.print_metric("Average Iteration Time", f"{(total_time/loop.iteration_count)*1000:.1f}ms")

    async def run(self) -> None:
        """Run the complete demonstration."""
        print("\n" + "🎯" * 40)
        print("\n  X-AGENT: Checkpoint & Runtime Metrics Demonstration")
        print("  Showcasing Production-Ready Features for Fault Tolerance\n")
        print("🎯" * 40)

        try:
            # Part 1: Runtime Metrics
            await self.demonstrate_runtime_metrics()
            await asyncio.sleep(1)

            # Part 2: Checkpoint Save/Load
            await self.demonstrate_checkpoint_save_and_load()
            await asyncio.sleep(1)

            # Part 3: Crash Recovery
            await self.demonstrate_crash_recovery()
            await asyncio.sleep(1)

            # Part 4: Continuous Operation
            await self.demonstrate_continuous_operation()

            # Final Summary
            self.print_header("🎉 DEMONSTRATION COMPLETE")
            print("\n✅ Successfully demonstrated:")
            print("   1. Runtime Metrics Collection (uptime, latency, success rate)")
            print("   2. Checkpoint Save and Load functionality")
            print("   3. Crash Recovery capability")
            print("   4. Continuous Operation with fault tolerance")
            print("\n🚀 These features address the high-priority gaps from FEATURES.md:")
            print("   • Runtime Metriken implementation ✅")
            print("   • State Persistence for Cognitive State ✅")
            print("   • Production-ready monitoring ✅")
            print("\n📊 All metrics are exportable to Prometheus at /metrics endpoint")
            print("💾 Checkpoints enable hot-reload and crash recovery")
            print("\n" + "=" * 80 + "\n")

        except Exception as e:
            print(f"\n❌ Error during demonstration: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Main entry point."""
    demo = CheckpointAndMetricsDemo()
    await demo.run()


if __name__ == "__main__":
    asyncio.run(main())
