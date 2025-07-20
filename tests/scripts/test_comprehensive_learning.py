#!/usr/bin/env python3
"""
NYX Active Learning System - Comprehensive Learning Test

Creates realistic historical data and demonstrates actual learning behavior.
Shows data-driven decision making, not just fallback modes.
"""

import asyncio
import sys
import traceback
import random
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Core imports
from database.connection import db_manager
from database.models import ThoughtTree, Agent, LLMInteraction, ToolExecution
from sqlalchemy import select
from core.learning.scorer import (
    performance_scorer, ScoringContext, update_thought_tree_scores
)
from core.learning.patterns import pattern_analyzer
from core.learning.adaptation import adaptive_engine
from core.learning.metrics import ComplexityLevel, baseline_manager
from config.settings import settings

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ComprehensiveLearningTest:
    """Comprehensive test that creates real data and demonstrates learning"""
    
    def __init__(self):
        self.cleanup_ids = []
        self.historical_data = []
    
    async def run_comprehensive_test(self) -> bool:
        """Run complete learning system test with real historical data"""
        
        print("🧠 COMPREHENSIVE NYX LEARNING SYSTEM TEST")
        print("=" * 60)
        print("Creating realistic historical data to demonstrate actual learning...")
        
        try:
            # Phase 1: Create substantial historical data
            print("\n📚 PHASE 1: Creating Historical Data")
            await self.create_historical_workflows()
            
            # Phase 2: Establish baselines from real data
            print("\n📊 PHASE 2: Establishing Baselines")
            await self.establish_baselines()
            
            # Phase 3: Test pattern recognition on real data
            print("\n🔍 PHASE 3: Pattern Recognition")
            patterns_result = await self.test_pattern_recognition()
            
            # Phase 4: Test data-driven recommendations
            print("\n🧠 PHASE 4: Data-Driven Recommendations")
            recommendations_result = await self.test_data_driven_decisions()
            
            # Phase 5: Test learning-based optimization
            print("\n⚡ PHASE 5: Learning-Based Optimization")
            optimization_result = await self.test_learning_optimization()
            
            # Phase 6: Demonstrate adaptive behavior
            print("\n🔄 PHASE 6: Adaptive Behavior")
            adaptation_result = await self.test_adaptive_behavior()
            
            # Calculate overall success
            results = [patterns_result, recommendations_result, optimization_result, adaptation_result]
            success_rate = sum(results) / len(results)
            
            print(f"\n📈 COMPREHENSIVE RESULTS")
            print(f"Pattern Recognition: {'✅ PASS' if patterns_result else '❌ FAIL'}")
            print(f"Data-Driven Decisions: {'✅ PASS' if recommendations_result else '❌ FAIL'}")
            print(f"Learning Optimization: {'✅ PASS' if optimization_result else '❌ FAIL'}")
            print(f"Adaptive Behavior: {'✅ PASS' if adaptation_result else '❌ FAIL'}")
            print(f"Overall Success Rate: {success_rate:.1%}")
            
            if success_rate >= 0.75:
                print("\n🎉 NYX LEARNING SYSTEM: FULLY OPERATIONAL WITH REAL LEARNING")
                return True
            else:
                print("\n❌ NYX LEARNING SYSTEM: PARTIAL FUNCTIONALITY")
                return False
                
        except Exception as e:
            print(f"💥 Comprehensive test failed: {str(e)}")
            traceback.print_exc()
            return False
        finally:
            await self.cleanup_test_data()
    
    async def create_historical_workflows(self) -> None:
        """Create realistic historical workflow data with varied outcomes"""
        
        # Define workflow scenarios with realistic characteristics
        scenarios = [
            # Fast, successful workflows
            {"strategy": "direct_execution", "success_rate": 0.9, "avg_time": 45, "complexity": ComplexityLevel.LOW, "cost_range": (15, 25)},
            {"strategy": "direct_execution", "success_rate": 0.85, "avg_time": 60, "complexity": ComplexityLevel.LOW, "cost_range": (18, 28)},
            
            # Medium complexity workflows
            {"strategy": "parallel_execution", "success_rate": 0.8, "avg_time": 120, "complexity": ComplexityLevel.MEDIUM, "cost_range": (30, 50)},
            {"strategy": "parallel_execution", "success_rate": 0.75, "avg_time": 150, "complexity": ComplexityLevel.MEDIUM, "cost_range": (35, 55)},
            {"strategy": "sequential_decomposition", "success_rate": 0.7, "avg_time": 180, "complexity": ComplexityLevel.MEDIUM, "cost_range": (40, 60)},
            
            # High complexity workflows
            {"strategy": "hierarchical_delegation", "success_rate": 0.6, "avg_time": 300, "complexity": ComplexityLevel.HIGH, "cost_range": (80, 120)},
            {"strategy": "hierarchical_delegation", "success_rate": 0.65, "avg_time": 280, "complexity": ComplexityLevel.HIGH, "cost_range": (75, 115)},
            
            # Some failed scenarios to show learning from failures
            {"strategy": "direct_execution", "success_rate": 0.3, "avg_time": 200, "complexity": ComplexityLevel.HIGH, "cost_range": (60, 90)},  # Wrong strategy for complexity
            {"strategy": "sequential_decomposition", "success_rate": 0.4, "avg_time": 100, "complexity": ComplexityLevel.LOW, "cost_range": (25, 35)},  # Overkill for simple task
        ]
        
        # Create 50+ historical workflows across different time periods
        base_time = datetime.now() - timedelta(days=60)  # 60 days of history
        
        for i in range(55):  # Create 55 workflows for statistical significance
            scenario = random.choice(scenarios)
            
            # Vary the timing to spread across history
            created_time = base_time + timedelta(days=random.uniform(0, 50))
            execution_time = random.gauss(scenario["avg_time"], scenario["avg_time"] * 0.2)  # 20% variance
            execution_time = max(30, execution_time)  # Minimum 30 seconds
            
            completed_time = created_time + timedelta(seconds=execution_time)
            
            # Determine success based on scenario success rate
            workflow_succeeded = random.random() < scenario["success_rate"]
            status = "completed" if workflow_succeeded else "failed"
            
            # Create thought tree
            async with db_manager.get_async_session() as session:
                thought_tree = ThoughtTree(
                    goal=f"Historical workflow {i+1}: {scenario['strategy']} task",
                    status=status,
                    depth=random.randint(1, 4),
                    importance_level=scenario["complexity"].value,
                    created_at=created_time,
                    completed_at=completed_time,
                    metadata_={
                        "execution_strategy": scenario["strategy"],
                        "workflow_type": "historical_simulation",
                        "complexity": {
                            "cognitive_complexity": scenario["complexity"].value,
                            "technical_complexity": random.choice(["low", "medium", "high"]),
                            "coordination_complexity": scenario["complexity"].value
                        },
                        "historical_test_data": True
                    }
                )
                session.add(thought_tree)
                await session.flush()
                
                thought_tree_id = thought_tree.id
                self.cleanup_ids.append(thought_tree_id)
                
                # Create realistic agents based on strategy
                agent_counts = {
                    "direct_execution": random.randint(1, 3),
                    "parallel_execution": random.randint(3, 8),
                    "sequential_decomposition": random.randint(2, 6),
                    "hierarchical_delegation": random.randint(5, 12)
                }
                
                agent_count = agent_counts[scenario["strategy"]]
                agents_succeeded = int(agent_count * scenario["success_rate"]) if workflow_succeeded else random.randint(0, agent_count//2)
                agents_failed = agent_count - agents_succeeded
                
                # Create agents
                for j in range(agents_succeeded):
                    agent = Agent(
                        thought_tree_id=thought_tree_id,
                        agent_type="task",
                        agent_class="task.TaskAgent",
                        status="completed",
                        created_at=created_time + timedelta(seconds=j*10),
                        completed_at=completed_time - timedelta(seconds=(agents_succeeded-j)*5)
                    )
                    session.add(agent)
                
                for j in range(agents_failed):
                    agent = Agent(
                        thought_tree_id=thought_tree_id,
                        agent_type="task", 
                        agent_class="task.TaskAgent",
                        status="failed",
                        created_at=created_time + timedelta(seconds=(agents_succeeded+j)*10),
                        completed_at=completed_time - timedelta(seconds=j*3)
                    )
                    session.add(agent)
                
                # Create realistic LLM interactions
                interaction_count = random.randint(agent_count, agent_count * 3)  # 1-3 interactions per agent
                cost_per_interaction = random.uniform(*scenario["cost_range"]) / interaction_count
                
                for j in range(interaction_count):
                    success = random.random() < scenario["success_rate"]
                    retry_count = 0 if success else random.randint(1, 3)
                    
                    interaction = LLMInteraction(
                        thought_tree_id=thought_tree_id,
                        provider="claude",
                        model="claude-3-sonnet-20240229",
                        prompt_text=f"Historical interaction {j+1}",
                        response_text=f"Historical response {j+1}",
                        token_count_input=random.randint(100, 500),
                        token_count_output=random.randint(50, 300),
                        cost_usd=Decimal(str(round(cost_per_interaction, 4))),
                        success=success,
                        retry_count=retry_count,
                        created_at=created_time + timedelta(seconds=j*15)
                    )
                    session.add(interaction)
                
                await session.commit()
                
                # Store for analysis
                self.historical_data.append({
                    "thought_tree_id": str(thought_tree_id),
                    "strategy": scenario["strategy"],
                    "complexity": scenario["complexity"],
                    "success_rate": agents_succeeded / agent_count,
                    "execution_time": execution_time,
                    "cost": cost_per_interaction * interaction_count,
                    "agent_count": agent_count
                })
        
        print(f"✅ Created {len(self.historical_data)} realistic historical workflows")
        
        # Show data distribution
        strategies = {}
        for data in self.historical_data:
            strategy = data["strategy"]
            strategies[strategy] = strategies.get(strategy, 0) + 1
        
        for strategy, count in strategies.items():
            print(f"   {strategy}: {count} workflows")
    
    async def establish_baselines(self) -> bool:
        """Establish baselines from the historical data"""
        
        # Force baseline calculation
        await baseline_manager.update_baselines()
        
        # Test baseline retrieval for different scenarios
        baselines = {}
        for complexity in [ComplexityLevel.LOW, ComplexityLevel.MEDIUM, ComplexityLevel.HIGH]:
            baseline = await baseline_manager.get_baseline_metrics(complexity, "historical_simulation")
            baselines[complexity] = baseline
        
        # Verify we have real baselines now
        baseline_count = sum(1 for b in baselines.values() if b is not None and b.sample_size >= 5)
        
        if baseline_count >= 2:
            print(f"✅ Established {baseline_count} baselines with sufficient data")
            for complexity, baseline in baselines.items():
                if baseline:
                    print(f"   {complexity.value}: {baseline.sample_size} samples, avg time {baseline.avg_execution_time:.1f}s")
            return True
        else:
            print(f"❌ Only {baseline_count} baselines established")
            return False
    
    async def test_pattern_recognition(self) -> bool:
        """Test pattern recognition on real historical data"""
        
        # Analyze patterns with real data
        strategy_patterns = await pattern_analyzer.analyze_strategy_patterns(
            time_window=timedelta(days=60),
            min_sample_size=3
        )
        
        agent_patterns = await pattern_analyzer.analyze_agent_performance_patterns(
            time_window=timedelta(days=60)
        )
        
        failure_patterns = await pattern_analyzer.detect_failure_patterns(
            time_window=timedelta(days=60),
            min_occurrences=2
        )
        
        optimization_opportunities = await pattern_analyzer.identify_optimization_opportunities()
        
        # Verify meaningful patterns were found
        checks = [
            len(strategy_patterns) > 0,
            sum(len(patterns) for patterns in agent_patterns.values()) > 0,
            len(failure_patterns) > 0,
            len(optimization_opportunities) > 0
        ]
        
        patterns_found = sum(checks)
        
        if patterns_found >= 3:
            print(f"✅ Pattern recognition found meaningful patterns:")
            print(f"   Strategy patterns: {len(strategy_patterns)}")
            print(f"   Agent patterns: {sum(len(p) for p in agent_patterns.values())}")
            print(f"   Failure patterns: {len(failure_patterns)}")
            print(f"   Optimization opportunities: {len(optimization_opportunities)}")
            
            # Show some example patterns
            if strategy_patterns:
                best_strategy = max(strategy_patterns.items(), key=lambda x: x[1].get("avg_success_rate", 0))
                print(f"   Best performing strategy: {best_strategy[0]} ({best_strategy[1]['avg_success_rate']:.2%} success)")
            
            return True
        else:
            print(f"❌ Pattern recognition found insufficient patterns ({patterns_found}/4)")
            return False
    
    async def test_data_driven_decisions(self) -> bool:
        """Test that the system makes data-driven recommendations"""
        
        # Test different scenarios to see if system recommends based on historical data
        test_scenarios = [
            # Should favor direct_execution for low complexity based on our historical data
            {
                "workflow_input": {"type": "simple_task", "content": "Simple analysis task"},
                "complexity": {"cognitive_complexity": "low", "technical_complexity": "low"},
                "expected_strategy_types": ["direct_execution"]
            },
            # Should favor parallel_execution for medium complexity
            {
                "workflow_input": {"type": "complex_task", "content": "Multi-part analysis with several components"},
                "complexity": {"cognitive_complexity": "medium", "technical_complexity": "medium"},
                "expected_strategy_types": ["parallel_execution", "sequential_decomposition"]
            },
            # Should favor hierarchical_delegation for high complexity
            {
                "workflow_input": {"type": "enterprise_task", "content": "Large-scale system design and implementation"},
                "complexity": {"cognitive_complexity": "high", "technical_complexity": "high"},
                "expected_strategy_types": ["hierarchical_delegation"]
            }
        ]
        
        correct_recommendations = 0
        
        for i, scenario in enumerate(test_scenarios):
            recommendation = await adaptive_engine.recommend_strategy(
                scenario["workflow_input"], scenario["complexity"]
            )
            
            strategy_recommended = recommendation.recommended_strategy
            is_data_driven = recommendation.confidence > 0.7  # High confidence suggests data-driven
            is_expected_strategy = strategy_recommended in scenario["expected_strategy_types"]
            
            print(f"   Scenario {i+1}: {strategy_recommended} (confidence: {recommendation.confidence:.3f})")
            
            if is_data_driven and is_expected_strategy:
                correct_recommendations += 1
                print(f"     ✅ Appropriate data-driven recommendation")
            elif is_expected_strategy:
                correct_recommendations += 0.5
                print(f"     ⚠️  Correct strategy but low confidence (may be heuristic)")
            else:
                print(f"     ❌ Unexpected strategy recommendation")
        
        success_rate = correct_recommendations / len(test_scenarios)
        
        if success_rate >= 0.7:
            print(f"✅ Data-driven decisions: {success_rate:.1%} appropriate recommendations")
            return True
        else:
            print(f"❌ Data-driven decisions: {success_rate:.1%} appropriate recommendations (below 70%)")
            return False
    
    async def test_learning_optimization(self) -> bool:
        """Test that system can optimize based on historical performance"""
        
        # Create performance history based on our historical data
        performance_history = []
        
        for data in self.historical_data[:20]:  # Use subset for parameter optimization
            performance_history.append({
                "execution_time": data["execution_time"],
                "success_rate": data["success_rate"],
                "agent_count": data["agent_count"],
                "cost_consumed": data["cost"],
                "strategy_used": data["strategy"]
            })
        
        # Test parameter optimization
        current_params = {
            "timeout_seconds": 300,
            "max_concurrent_agents": 10,
            "max_retries": 3,
            "quality_threshold": 0.7
        }
        
        optimizations = await adaptive_engine.optimize_parameters(
            current_params, performance_history, {"complexity_level": "medium"}
        )
        
        # Verify optimizations are data-driven
        has_meaningful_optimizations = len(optimizations) > 0
        has_justified_changes = any(
            opt.get("confidence", 0) > 0.6 for opt in optimizations
        )
        
        if has_meaningful_optimizations and has_justified_changes:
            print(f"✅ Learning optimization: {len(optimizations)} data-driven optimizations found")
            for opt in optimizations[:3]:  # Show top 3
                print(f"   {opt.get('parameter', 'unknown')}: {opt.get('recommendation', 'N/A')} (confidence: {opt.get('confidence', 0):.2f})")
            return True
        else:
            print(f"❌ Learning optimization: Insufficient or low-confidence optimizations")
            return False
    
    async def test_adaptive_behavior(self) -> bool:
        """Test that system adapts behavior based on performance feedback"""
        
        # Simulate poor performance scenario
        poor_performance = {
            "execution_time": 600.0,  # Much slower than expected
            "cost_consumed": 150.0,   # High cost
            "success_rate": 0.3,      # Low success
            "failure_rate": 0.7       # High failure
        }
        
        expected_performance = {
            "execution_time": 180.0,
            "cost_estimate": 45.0,
            "success_rate": 0.8
        }
        
        context = {"current_strategy": "direct_execution", "complexity_level": "medium"}
        
        # Test adaptation recommendation
        adaptation = await adaptive_engine.should_adapt_workflow(
            poor_performance, expected_performance, context
        )
        
        # Verify system recommends adaptation for poor performance
        should_adapt = adaptation is not None
        has_urgency = adaptation and adaptation.urgency in ["medium", "high", "critical"]
        has_strategy_change = adaptation and adaptation.recommended_changes and len(adaptation.recommended_changes) > 0
        
        if should_adapt and has_urgency and has_strategy_change:
            print(f"✅ Adaptive behavior: System recommends {adaptation.urgency} adaptation")
            print(f"   Recommended changes: {len(adaptation.recommended_changes)}")
            for change in adaptation.recommended_changes[:2]:
                print(f"   - {change}")
            return True
        else:
            print(f"❌ Adaptive behavior: System failed to recommend appropriate adaptation")
            return False
    
    async def cleanup_test_data(self) -> None:
        """Clean up all test data"""
        
        if not self.cleanup_ids:
            return
        
        try:
            async with db_manager.get_async_session() as session:
                print(f"\n🧹 Cleaning up {len(self.cleanup_ids)} historical workflows...")
                
                # Delete related records first
                for table in [LLMInteraction, ToolExecution, Agent]:
                    for thought_tree_id in self.cleanup_ids:
                        records = await session.execute(
                            select(table).filter(table.thought_tree_id == thought_tree_id)
                        )
                        for record in records.scalars():
                            await session.delete(record)
                
                # Delete thought trees
                for thought_tree_id in self.cleanup_ids:
                    thought_tree = await session.get(ThoughtTree, thought_tree_id)
                    if thought_tree:
                        await session.delete(thought_tree)
                
                await session.commit()
                print("✅ Comprehensive test data cleaned up")
                
        except Exception as e:
            logger.error(f"Error cleaning up test data: {e}")


async def main() -> bool:
    """Run comprehensive learning system test"""
    
    test_suite = ComprehensiveLearningTest()
    
    try:
        return await test_suite.run_comprehensive_test()
    except Exception as e:
        print(f"💥 Comprehensive test execution failed: {str(e)}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)