"""
NYX Learning System - Scorer Module

Implements multi-dimensional performance scoring for the NYX orchestration system.
Calculates speed, quality, success, and usefulness scores with complexity adjustment.
"""

import asyncio
import time
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum

# System imports
from database.connection import db_manager
from database.models import ThoughtTree, Agent, LLMInteraction, ToolExecution, Orchestrator
from config.settings import settings
from .metrics import metrics_calculator, baseline_manager, PerformanceMetrics, ComplexityLevel
from sqlalchemy import select

import logging
logger = logging.getLogger(__name__)


@dataclass
class ScoringContext:
    """Context information for scoring calculations"""
    thought_tree_id: str
    workflow_type: Optional[str] = None
    complexity_level: ComplexityLevel = ComplexityLevel.MEDIUM
    user_feedback: Optional[float] = None
    goal_alignment: Optional[float] = None
    business_impact: float = 0.5
    validation_results: Optional[List[Dict]] = None
    custom_weights: Optional[Dict[str, float]] = None


@dataclass
class ScoringResult:
    """Result of multi-dimensional scoring calculation"""
    speed_score: float
    quality_score: float
    success_score: float
    usefulness_score: float
    composite_score: float
    confidence: float
    calculation_time: datetime
    baseline_used: bool
    
    # Supporting data
    execution_metrics: PerformanceMetrics
    scoring_context: ScoringContext
    notes: List[str]


class PerformanceScorer:
    """Multi-dimensional performance scorer for NYX system components"""
    
    def __init__(self):
        self.default_weights = {
            "speed": 0.25,
            "quality": 0.30,
            "success": 0.35,
            "usefulness": 0.10
        }
    
    async def score_workflow_execution(
        self,
        thought_tree_id: str,
        start_time: datetime,
        end_time: datetime,
        context: ScoringContext
    ) -> ScoringResult:
        """Score a complete workflow execution with all dimensions"""
        
        calculation_start = time.time()
        notes = []
        
        try:
            # Calculate execution metrics
            metrics = await metrics_calculator.calculate_execution_metrics(
                thought_tree_id, start_time, end_time
            )
            
            # Update context with calculated complexity if not provided
            if context.complexity_level == ComplexityLevel.MEDIUM and metrics.complexity_level != ComplexityLevel.MEDIUM:
                context.complexity_level = metrics.complexity_level
                notes.append(f"Complexity level adjusted to {metrics.complexity_level.value}")
            
            # Calculate individual dimension scores
            speed_score = await self._calculate_speed_score(metrics, context)
            quality_score = await self._calculate_quality_score(metrics, context)
            success_score = await self._calculate_success_score(metrics, context)
            usefulness_score = await self._calculate_usefulness_score(metrics, context)
            
            # Calculate composite score
            composite_score = await self._calculate_composite_score(
                speed_score, quality_score, success_score, usefulness_score, context
            )
            
            # Calculate confidence based on data availability
            confidence = self._calculate_confidence(metrics, context)
            
            # Check if baseline was used
            baseline = await baseline_manager.get_baseline_metrics(
                context.complexity_level, context.workflow_type
            )
            baseline_used = baseline is not None
            
            if not baseline_used:
                notes.append("No baseline available - using default scoring")
            
            return ScoringResult(
                speed_score=speed_score,
                quality_score=quality_score,
                success_score=success_score,
                usefulness_score=usefulness_score,
                composite_score=composite_score,
                confidence=confidence,
                calculation_time=datetime.now(),
                baseline_used=baseline_used,
                execution_metrics=metrics,
                scoring_context=context,
                notes=notes
            )
            
        except Exception as e:
            logger.error(f"Error calculating scores for {thought_tree_id}: {e}")
            # Return minimal scoring result
            return ScoringResult(
                speed_score=0.5,
                quality_score=0.5,
                success_score=0.5,
                usefulness_score=0.5,
                composite_score=0.5,
                confidence=0.1,
                calculation_time=datetime.now(),
                baseline_used=False,
                execution_metrics=PerformanceMetrics(
                    execution_time=(end_time - start_time).total_seconds(),
                    success_rate=0.5,
                    token_usage=0,
                    cost_usd=Decimal('0'),
                    agent_count=0,
                    retry_count=0,
                    complexity_level=context.complexity_level,
                    timestamp=end_time
                ),
                scoring_context=context,
                notes=[f"Error in calculation: {str(e)}"]
            )
        finally:
            calc_time = time.time() - calculation_start
            logger.debug(f"Scoring calculation took {calc_time:.3f}s for {thought_tree_id}")
    
    async def _calculate_speed_score(
        self,
        metrics: PerformanceMetrics,
        context: ScoringContext
    ) -> float:
        """Calculate speed score based on execution time vs baseline"""
        
        return await metrics_calculator.calculate_speed_score(
            metrics.execution_time,
            context.complexity_level,
            context.workflow_type
        )
    
    async def _calculate_quality_score(
        self,
        metrics: PerformanceMetrics,
        context: ScoringContext
    ) -> float:
        """Calculate quality score based on success rate, retries, and validation"""
        
        return await metrics_calculator.calculate_quality_score(
            metrics.success_rate,
            metrics.retry_count,
            context.validation_results
        )
    
    async def _calculate_success_score(
        self,
        metrics: PerformanceMetrics,
        context: ScoringContext
    ) -> float:
        """Calculate success score from execution outcome data"""
        
        # Get agent success/failure counts from thought tree
        async with db_manager.get_async_session() as session:
            agents = await session.execute(
                select(Agent).filter(Agent.thought_tree_id == context.thought_tree_id)
            )
            agents = agents.scalars().all()
            
            agents_succeeded = sum(1 for agent in agents if agent.status == "completed")
            agents_failed = sum(1 for agent in agents if agent.status == "failed")
            
            # Check for critical failures (orchestrator failures)
            orchestrators = await session.execute(
                select(Orchestrator).filter(Orchestrator.thought_tree_id == context.thought_tree_id)
            )
            orchestrators = orchestrators.scalars().all()
            critical_failures = sum(1 for orch in orchestrators if orch.status == "failed")
            
            # Determine overall success from thought tree status
            thought_tree = await session.get(ThoughtTree, context.thought_tree_id)
            overall_success = thought_tree and thought_tree.status == "completed"
            
            return metrics_calculator.calculate_success_score(
                agents_succeeded, agents_failed, overall_success, critical_failures
            )
    
    async def _calculate_usefulness_score(
        self,
        metrics: PerformanceMetrics,
        context: ScoringContext
    ) -> float:
        """Calculate usefulness score based on goal alignment and impact"""
        
        # Use provided goal alignment or calculate from metadata
        goal_alignment = context.goal_alignment
        if goal_alignment is None:
            goal_alignment = await self._estimate_goal_alignment(context.thought_tree_id)
        
        return metrics_calculator.calculate_usefulness_score(
            goal_alignment,
            context.user_feedback,
            context.business_impact
        )
    
    async def _estimate_goal_alignment(self, thought_tree_id: str) -> float:
        """Estimate goal alignment from thought tree completion and agent success"""
        
        async with db_manager.get_async_session() as session:
            thought_tree = await session.get(ThoughtTree, thought_tree_id)
            if not thought_tree:
                return 0.5
            
            # Base alignment on completion status
            if thought_tree.status == "completed":
                base_alignment = 0.8
            elif thought_tree.status == "failed":
                base_alignment = 0.2
            else:
                base_alignment = 0.5
            
            # Adjust based on agent success rates
            agents = await session.execute(
                select(Agent).filter(Agent.thought_tree_id == thought_tree_id)
            )
            agents = agents.scalars().all()
            
            if agents:
                completed_agents = sum(1 for agent in agents if agent.status == "completed")
                agent_success_rate = completed_agents / len(agents)
                # Weight base alignment (70%) and agent success (30%)
                base_alignment = (base_alignment * 0.7) + (agent_success_rate * 0.3)
            
            return min(1.0, max(0.0, base_alignment))
    
    async def _calculate_composite_score(
        self,
        speed_score: float,
        quality_score: float,
        success_score: float,
        usefulness_score: float,
        context: ScoringContext
    ) -> float:
        """Calculate weighted composite score from individual dimensions"""
        
        # Use custom weights if provided, otherwise use defaults
        weights = context.custom_weights or self.default_weights
        
        # Normalize weights to ensure they sum to 1.0
        total_weight = sum(weights.values())
        if total_weight == 0:
            weights = self.default_weights
            total_weight = sum(weights.values())
        
        normalized_weights = {k: v / total_weight for k, v in weights.items()}
        
        # Calculate weighted composite
        composite = (
            speed_score * normalized_weights.get("speed", 0.25) +
            quality_score * normalized_weights.get("quality", 0.30) +
            success_score * normalized_weights.get("success", 0.35) +
            usefulness_score * normalized_weights.get("usefulness", 0.10)
        )
        
        return min(1.0, max(0.0, composite))
    
    def _calculate_confidence(
        self,
        metrics: PerformanceMetrics,
        context: ScoringContext
    ) -> float:
        """Calculate confidence in scoring accuracy based on data availability"""
        
        confidence_factors = []
        
        # Baseline availability
        baseline = baseline_manager.cache.get(
            f"{context.complexity_level.value}_{context.workflow_type}_{30}"
        )
        if baseline and baseline[0]:
            confidence_factors.append(0.3)  # 30% for good baseline
        else:
            confidence_factors.append(0.1)  # 10% without baseline
        
        # Agent count (more agents = more data points)
        if metrics.agent_count >= 5:
            confidence_factors.append(0.25)
        elif metrics.agent_count >= 3:
            confidence_factors.append(0.15)
        else:
            confidence_factors.append(0.05)
        
        # Validation results availability
        if context.validation_results:
            confidence_factors.append(0.2)
        else:
            confidence_factors.append(0.1)
        
        # User feedback availability
        if context.user_feedback is not None:
            confidence_factors.append(0.15)
        else:
            confidence_factors.append(0.05)
        
        # Goal alignment specification
        if context.goal_alignment is not None:
            confidence_factors.append(0.1)
        else:
            confidence_factors.append(0.05)
        
        return min(1.0, sum(confidence_factors))


class BatchScorer:
    """Efficient batch scoring for multiple workflows"""
    
    def __init__(self, scorer: PerformanceScorer):
        self.scorer = scorer
    
    async def score_multiple_workflows(
        self,
        workflow_specs: List[Tuple[str, datetime, datetime, ScoringContext]]
    ) -> List[ScoringResult]:
        """Score multiple workflows efficiently in batch"""
        
        logger.info(f"Batch scoring {len(workflow_specs)} workflows")
        
        # Create semaphore to limit concurrent scoring
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent scorings
        
        async def score_single(spec):
            async with semaphore:
                thought_tree_id, start_time, end_time, context = spec
                return await self.scorer.score_workflow_execution(
                    thought_tree_id, start_time, end_time, context
                )
        
        # Execute all scorings concurrently
        results = await asyncio.gather(
            *[score_single(spec) for spec in workflow_specs],
            return_exceptions=True
        )
        
        # Filter out exceptions and log errors
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error scoring workflow {workflow_specs[i][0]}: {result}")
            else:
                valid_results.append(result)
        
        logger.info(f"Successfully scored {len(valid_results)}/{len(workflow_specs)} workflows")
        return valid_results


async def update_thought_tree_scores(
    thought_tree_id: str,
    scoring_result: ScoringResult
) -> None:
    """Update thought tree with calculated scores"""
    
    try:
        async with db_manager.get_async_session() as session:
            thought_tree = await session.get(ThoughtTree, thought_tree_id)
            if not thought_tree:
                logger.error(f"ThoughtTree {thought_tree_id} not found for score update")
                return
            
            # Update scores
            thought_tree.success_score = Decimal(str(round(scoring_result.success_score, 4)))
            thought_tree.quality_score = Decimal(str(round(scoring_result.quality_score, 4)))
            thought_tree.speed_score = Decimal(str(round(scoring_result.speed_score, 4)))
            thought_tree.usefulness_score = Decimal(str(round(scoring_result.usefulness_score, 4)))
            thought_tree.overall_weight = Decimal(str(round(scoring_result.composite_score, 4)))
            
            # Update metadata with scoring details
            if not thought_tree.metadata_:
                thought_tree.metadata_ = {}
            
            thought_tree.metadata_["scoring"] = {
                "confidence": scoring_result.confidence,
                "calculation_time": scoring_result.calculation_time.isoformat(),
                "baseline_used": scoring_result.baseline_used,
                "notes": scoring_result.notes,
                "execution_metrics": {
                    "execution_time": scoring_result.execution_metrics.execution_time,
                    "success_rate": scoring_result.execution_metrics.success_rate,
                    "token_usage": scoring_result.execution_metrics.token_usage,
                    "cost_usd": float(scoring_result.execution_metrics.cost_usd),
                    "agent_count": scoring_result.execution_metrics.agent_count,
                    "retry_count": scoring_result.execution_metrics.retry_count
                }
            }
            
            # Tell SQLAlchemy the JSON field has been modified
            from sqlalchemy.orm import attributes
            attributes.flag_modified(thought_tree, "metadata_")
            
            await session.commit()
            logger.info(f"Updated scores for ThoughtTree {thought_tree_id}")
            
    except Exception as e:
        logger.error(f"Error updating scores for {thought_tree_id}: {e}")
        await session.rollback()
        raise


# Global scorer instance
performance_scorer = PerformanceScorer()
batch_scorer = BatchScorer(performance_scorer)