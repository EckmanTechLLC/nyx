#!/usr/bin/env python3
"""
NYX Active Learning System - Scoring System Test

Tests the multi-dimensional scoring algorithms and database integration.
Validates scoring accuracy, performance, and database persistence.
"""

import asyncio
import sys
import traceback
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Core imports
from database.connection import db_manager
from database.models import ThoughtTree, Agent, LLMInteraction, ToolExecution
from sqlalchemy import select
from core.learning.scorer import (
    PerformanceScorer, ScoringContext, ScoringResult,
    update_thought_tree_scores, batch_scorer
)
from core.learning.metrics import (
    ComplexityLevel, MetricsCalculator, BaselineManager,
    metrics_calculator, baseline_manager
)
from config.settings import settings

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScoringSystemTest:
    """Comprehensive test suite for the scoring system"""
    
    def __init__(self):
        self.scorer = PerformanceScorer()
        self.test_data = {}
        self.cleanup_ids = []
    
    async def run_all_tests(self) -> bool:
        """Run all scoring system tests"""
        
        print("🔍 TESTING NYX SCORING SYSTEM")
        print("=" * 50)
        
        try:
            # Setup test data
            await self.setup_test_data()
            
            # Test individual components
            tests = [
                ("Metrics Calculator", self.test_metrics_calculator),
                ("Basic Scoring", self.test_basic_scoring),
                ("Database Integration", self.test_database_integration),
                ("Baseline Manager", self.test_baseline_manager),
                ("Batch Scoring", self.test_batch_scoring),
                ("Performance Tests", self.test_performance)
            ]
            
            passed = 0
            for test_name, test_func in tests:
                print(f"\n📊 Testing {test_name}...")
                try:
                    result = await test_func()
                    if result:
                        print(f"✅ {test_name}: PASSED")
                        passed += 1
                    else:
                        print(f"❌ {test_name}: FAILED")
                except Exception as e:
                    print(f"💥 {test_name}: ERROR - {str(e)}")
                    traceback.print_exc()
            
            success_rate = passed / len(tests)
            print(f"\n📈 RESULTS: {passed}/{len(tests)} tests passed ({success_rate:.1%})")
            
            if success_rate >= 0.8:
                print("🎉 SCORING SYSTEM: OPERATIONAL")
                return True
            else:
                print("❌ SCORING SYSTEM: NEEDS ATTENTION")
                return False
                
        except Exception as e:
            print(f"💥 Test suite failed: {str(e)}")
            traceback.print_exc()
            return False
        finally:
            await self.cleanup_test_data()
    
    async def setup_test_data(self) -> None:
        """Create test data for scoring tests"""
        
        print("🔧 Setting up test data...")
        
        async with db_manager.get_async_session() as session:
            # Create test thought tree
            thought_tree = ThoughtTree(
                goal="Test workflow for scoring validation",
                status="completed",
                depth=1,
                created_at=datetime.now() - timedelta(minutes=5),
                completed_at=datetime.now(),
                metadata_={
                    "workflow_type": "test_workflow",
                    "complexity": {
                        "cognitive_complexity": "medium",
                        "technical_complexity": "low",
                        "coordination_complexity": "low"
                    },
                    "agent_count": 3
                }
            )
            session.add(thought_tree)
            await session.flush()
            
            self.test_data["thought_tree_id"] = str(thought_tree.id)
            self.cleanup_ids.append(thought_tree.id)
            
            # Create test agents
            agents_data = [
                {"status": "completed", "agent_type": "task"},
                {"status": "completed", "agent_type": "task"},
                {"status": "failed", "agent_type": "validator"}
            ]
            
            for agent_data in agents_data:
                agent = Agent(
                    thought_tree_id=thought_tree.id,
                    agent_type=agent_data["agent_type"],
                    agent_class=f"{agent_data['agent_type']}.Agent",
                    status=agent_data["status"],
                    created_at=datetime.now() - timedelta(minutes=4),
                    completed_at=datetime.now() - timedelta(minutes=1)
                )
                session.add(agent)
            
            # Create test LLM interactions
            llm_interactions = [
                {
                    "token_count_input": 150,
                    "token_count_output": 75,
                    "cost_usd": Decimal("0.0025"),
                    "latency_ms": 850,
                    "success": True,
                    "retry_count": 0
                },
                {
                    "token_count_input": 200,
                    "token_count_output": 100,
                    "cost_usd": Decimal("0.0033"),
                    "latency_ms": 1200,
                    "success": True,
                    "retry_count": 1
                }
            ]
            
            for llm_data in llm_interactions:
                interaction = LLMInteraction(
                    thought_tree_id=thought_tree.id,
                    provider="claude",
                    model="claude-3-sonnet-20240229",
                    prompt_text="Test prompt",
                    response_text="Test response",
                    **llm_data
                )
                session.add(interaction)
            
            await session.commit()
        
        print("✅ Test data created")
    
    async def test_metrics_calculator(self) -> bool:
        """Test metrics calculation functionality"""
        
        thought_tree_id = self.test_data["thought_tree_id"]
        start_time = datetime.now() - timedelta(minutes=5)
        end_time = datetime.now()
        
        # Test metrics calculation
        metrics = await metrics_calculator.calculate_execution_metrics(
            thought_tree_id, start_time, end_time
        )
        
        # Validate metrics
        checks = [
            metrics.execution_time > 0,
            0.0 <= metrics.success_rate <= 1.0,
            metrics.token_usage > 0,
            metrics.cost_usd > 0,
            metrics.agent_count == 3,
            isinstance(metrics.complexity_level, ComplexityLevel)
        ]
        
        if all(checks):
            print(f"  📊 Metrics: {metrics.execution_time:.1f}s, {metrics.success_rate:.2f} success, {metrics.token_usage} tokens")
            return True
        else:
            print(f"  ❌ Metrics validation failed: {checks}")
            return False
    
    async def test_basic_scoring(self) -> bool:
        """Test basic scoring algorithm functionality"""
        
        thought_tree_id = self.test_data["thought_tree_id"]
        start_time = datetime.now() - timedelta(minutes=5)
        end_time = datetime.now()
        
        # Create scoring context
        context = ScoringContext(
            thought_tree_id=thought_tree_id,
            workflow_type="test_workflow",
            complexity_level=ComplexityLevel.MEDIUM,
            goal_alignment=0.8,
            business_impact=0.6
        )
        
        # Calculate scores
        result = await self.scorer.score_workflow_execution(
            thought_tree_id, start_time, end_time, context
        )
        
        # Validate scoring result
        checks = [
            isinstance(result, ScoringResult),
            0.0 <= result.speed_score <= 1.0,
            0.0 <= result.quality_score <= 1.0,
            0.0 <= result.success_score <= 1.0,
            0.0 <= result.usefulness_score <= 1.0,
            0.0 <= result.composite_score <= 1.0,
            0.0 <= result.confidence <= 1.0,
            len(result.notes) >= 0
        ]
        
        if all(checks):
            print(f"  📊 Scores: Speed={result.speed_score:.3f}, Quality={result.quality_score:.3f}, Success={result.success_score:.3f}, Usefulness={result.usefulness_score:.3f}")
            print(f"  🎯 Composite: {result.composite_score:.3f} (confidence: {result.confidence:.3f})")
            return True
        else:
            print(f"  ❌ Scoring validation failed: {checks}")
            return False
    
    async def test_database_integration(self) -> bool:
        """Test database score update functionality"""
        
        thought_tree_id = self.test_data["thought_tree_id"]
        start_time = datetime.now() - timedelta(minutes=5)
        end_time = datetime.now()
        
        context = ScoringContext(
            thought_tree_id=thought_tree_id,
            workflow_type="test_workflow",
            complexity_level=ComplexityLevel.MEDIUM,
            goal_alignment=0.85,
            business_impact=0.7
        )
        
        # Calculate scores
        result = await self.scorer.score_workflow_execution(
            thought_tree_id, start_time, end_time, context
        )
        
        # Update database
        await update_thought_tree_scores(thought_tree_id, result)
        
        # Verify database update
        async with db_manager.get_async_session() as session:
            thought_tree = await session.get(ThoughtTree, thought_tree_id)
            
            print(f"  🔍 DEBUG: thought_tree is not None: {thought_tree is not None}")
            if thought_tree:
                print(f"  🔍 DEBUG: success_score DB={thought_tree.success_score}, expected={round(result.success_score, 4)}")
                print(f"  🔍 DEBUG: quality_score DB={thought_tree.quality_score}, expected={round(result.quality_score, 4)}")
                print(f"  🔍 DEBUG: speed_score DB={thought_tree.speed_score}, expected={round(result.speed_score, 4)}")
                print(f"  🔍 DEBUG: usefulness_score DB={thought_tree.usefulness_score}, expected={round(result.usefulness_score, 4)}")
                print(f"  🔍 DEBUG: overall_weight DB={thought_tree.overall_weight}, expected={round(result.composite_score, 4)}")
                print(f"  🔍 DEBUG: metadata_ type: {type(thought_tree.metadata_)}")
                print(f"  🔍 DEBUG: metadata_ content: {thought_tree.metadata_}")
                print(f"  🔍 DEBUG: 'scoring' in metadata: {'scoring' in thought_tree.metadata_ if thought_tree.metadata_ else 'metadata is None'}")
            
            checks = [
                thought_tree is not None,
                float(thought_tree.success_score) == round(result.success_score, 4),
                float(thought_tree.quality_score) == round(result.quality_score, 4),
                float(thought_tree.speed_score) == round(result.speed_score, 4),
                float(thought_tree.usefulness_score) == round(result.usefulness_score, 4),
                float(thought_tree.overall_weight) == round(result.composite_score, 4),
                "scoring" in thought_tree.metadata_
            ]
            
            print(f"  🔍 DEBUG: Individual checks: {checks}")
            
            if all(checks):
                print(f"  💾 Database updated successfully")
                print(f"  📊 Stored scores: Success={thought_tree.success_score}, Quality={thought_tree.quality_score}")
                return True
            else:
                print(f"  ❌ Database integration failed: {checks}")
                return False
    
    async def test_baseline_manager(self) -> bool:
        """Test baseline calculation and caching"""
        
        # Test baseline calculation (may return None if insufficient data)
        baseline = await baseline_manager.get_baseline_metrics(
            ComplexityLevel.MEDIUM, "test_workflow"
        )
        
        # Test cache functionality
        cache_key = f"{ComplexityLevel.MEDIUM.value}_test_workflow_30"
        cached_before = cache_key in baseline_manager.cache
        
        # Second call should use cache
        baseline2 = await baseline_manager.get_baseline_metrics(
            ComplexityLevel.MEDIUM, "test_workflow"
        )
        
        cached_after = cache_key in baseline_manager.cache
        
        # Validate (baseline may be None with insufficient data)
        checks = [
            baseline == baseline2,  # Same result from cache
            cached_after or baseline is None  # Either cached or no data
        ]
        
        if all(checks):
            if baseline:
                print(f"  📈 Baseline: {baseline.avg_execution_time:.1f}s avg, {baseline.sample_size} samples")
            else:
                print(f"  📈 No baseline data (insufficient samples) - this is normal for test data")
            return True
        else:
            print(f"  ❌ Baseline manager failed: {checks}")
            return False
    
    async def test_batch_scoring(self) -> bool:
        """Test batch scoring functionality"""
        
        thought_tree_id = self.test_data["thought_tree_id"]
        start_time = datetime.now() - timedelta(minutes=5)
        end_time = datetime.now()
        
        # Create batch of scoring requests
        batch_specs = []
        for i in range(3):
            context = ScoringContext(
                thought_tree_id=thought_tree_id,
                workflow_type="test_workflow",
                complexity_level=ComplexityLevel.MEDIUM,
                goal_alignment=0.7 + (i * 0.1),
                business_impact=0.5 + (i * 0.1)
            )
            batch_specs.append((thought_tree_id, start_time, end_time, context))
        
        # Execute batch scoring
        results = await batch_scorer.score_multiple_workflows(batch_specs)
        
        # Validate results
        checks = [
            len(results) == len(batch_specs),
            all(isinstance(r, ScoringResult) for r in results),
            all(0.0 <= r.composite_score <= 1.0 for r in results)
        ]
        
        if all(checks):
            avg_composite = sum(r.composite_score for r in results) / len(results)
            print(f"  🔄 Batch scoring: {len(results)} results, avg composite: {avg_composite:.3f}")
            return True
        else:
            print(f"  ❌ Batch scoring failed: {checks}")
            return False
    
    async def test_performance(self) -> bool:
        """Test scoring performance and efficiency"""
        
        thought_tree_id = self.test_data["thought_tree_id"]
        start_time = datetime.now() - timedelta(minutes=5)
        end_time = datetime.now()
        
        context = ScoringContext(
            thought_tree_id=thought_tree_id,
            workflow_type="test_workflow"
        )
        
        # Time scoring operation
        perf_start = datetime.now()
        result = await self.scorer.score_workflow_execution(
            thought_tree_id, start_time, end_time, context
        )
        perf_duration = (datetime.now() - perf_start).total_seconds()
        
        # Performance requirements
        checks = [
            perf_duration < 1.0,  # Should complete within 1 second
            isinstance(result, ScoringResult),
            result.confidence > 0.0
        ]
        
        if all(checks):
            print(f"  ⚡ Performance: Scoring completed in {perf_duration:.3f}s (target: <1.0s)")
            return True
        else:
            print(f"  ❌ Performance test failed: {perf_duration:.3f}s, checks: {checks}")
            return False
    
    async def cleanup_test_data(self) -> None:
        """Clean up test data"""
        
        if not self.cleanup_ids:
            return
        
        try:
            async with db_manager.get_async_session() as session:
                # Delete related records first (foreign key constraints)
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
                print("🧹 Test data cleaned up")
                
        except Exception as e:
            logger.error(f"Error cleaning up test data: {e}")


async def main() -> bool:
    """Run scoring system tests"""
    
    test_suite = ScoringSystemTest()
    
    try:
        return await test_suite.run_all_tests()
    except Exception as e:
        print(f"💥 Test execution failed: {str(e)}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)