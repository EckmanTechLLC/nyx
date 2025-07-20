"""
NYX Learning System - Metrics Module

Provides standardized calculation of performance metrics across all system components.
Handles baseline establishment, complexity-adjusted scoring, and trend analysis.
"""

import asyncio
import time
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# System imports
from database.connection import db_manager
from database.models import ThoughtTree, Agent, LLMInteraction, ToolExecution
from config.settings import settings
from sqlalchemy import func, and_, desc, select
from sqlalchemy.orm import selectinload

import logging
logger = logging.getLogger(__name__)


class ComplexityLevel(Enum):
    """Complexity levels for performance adjustment"""
    LOW = "low"
    MEDIUM = "medium"  
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics for a workflow/agent"""
    execution_time: float
    success_rate: float
    token_usage: int
    cost_usd: Decimal
    agent_count: int
    retry_count: int
    complexity_level: ComplexityLevel
    timestamp: datetime
    
    # Calculated scores
    speed_score: Optional[float] = None
    quality_score: Optional[float] = None
    success_score: Optional[float] = None
    usefulness_score: Optional[float] = None


@dataclass
class BaselineMetrics:
    """Baseline performance metrics for comparison"""
    avg_execution_time: float
    median_execution_time: float
    avg_success_rate: float
    avg_token_usage: int
    avg_cost_usd: Decimal
    sample_size: int
    complexity_level: ComplexityLevel
    last_updated: datetime


class MetricsCalculator:
    """Calculates standardized performance metrics across all system components"""
    
    def __init__(self):
        self.baseline_cache = {}
        self.cache_ttl = timedelta(hours=1)
    
    async def calculate_execution_metrics(
        self,
        thought_tree_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> PerformanceMetrics:
        """Calculate comprehensive metrics for a workflow execution"""
        
        async with db_manager.get_async_session() as session:
            # Get thought tree details
            thought_tree = await session.get(ThoughtTree, thought_tree_id)
            if not thought_tree:
                raise ValueError(f"ThoughtTree {thought_tree_id} not found")
            
            # Get all related agents
            agents = await session.execute(
                select(Agent)
                .filter(Agent.thought_tree_id == thought_tree_id)
                .options(selectinload(Agent.llm_interactions))
            )
            agents = agents.scalars().all()
            
            # Get all LLM interactions
            llm_interactions = await session.execute(
                select(LLMInteraction)
                .filter(LLMInteraction.thought_tree_id == thought_tree_id)
            )
            llm_interactions = llm_interactions.scalars().all()
            
            # Get all tool executions
            tool_executions = await session.execute(
                select(ToolExecution)
                .filter(ToolExecution.thought_tree_id == thought_tree_id)
            )
            tool_executions = tool_executions.scalars().all()
            
            # Calculate metrics
            execution_time = (end_time - start_time).total_seconds()
            
            # Success metrics
            completed_agents = sum(1 for agent in agents if agent.status == "completed")
            failed_agents = sum(1 for agent in agents if agent.status == "failed")
            total_agents = len(agents)
            success_rate = completed_agents / max(total_agents, 1)
            
            # Token and cost metrics
            total_tokens = sum(
                (interaction.token_count_input or 0) + (interaction.token_count_output or 0)
                for interaction in llm_interactions
            )
            total_cost = sum(
                interaction.cost_usd or Decimal('0')
                for interaction in llm_interactions
            )
            
            # Retry metrics
            total_retries = sum(
                interaction.retry_count or 0
                for interaction in llm_interactions
            ) + sum(
                execution.retry_count or 0
                for execution in tool_executions
            )
            
            # Determine complexity level from thought tree metadata
            complexity_level = self._determine_complexity_level(thought_tree.metadata_)
            
            return PerformanceMetrics(
                execution_time=execution_time,
                success_rate=success_rate,
                token_usage=total_tokens,
                cost_usd=total_cost,
                agent_count=total_agents,
                retry_count=total_retries,
                complexity_level=complexity_level,
                timestamp=end_time
            )
    
    def _determine_complexity_level(self, metadata: Dict) -> ComplexityLevel:
        """Determine complexity level from thought tree metadata"""
        if not metadata:
            return ComplexityLevel.MEDIUM
            
        complexity_indicators = metadata.get("complexity", {})
        
        # Use orchestrator complexity analysis if available
        if "cognitive_complexity" in complexity_indicators:
            high_complexity_count = sum(
                1 for level in complexity_indicators.values()
                if level == "high"
            )
            if high_complexity_count >= 3:
                return ComplexityLevel.CRITICAL
            elif high_complexity_count >= 2:
                return ComplexityLevel.HIGH
            elif high_complexity_count >= 1:
                return ComplexityLevel.MEDIUM
            else:
                return ComplexityLevel.LOW
        
        # Fallback to simple heuristics
        agent_count = metadata.get("agent_count", 1)
        depth = metadata.get("depth", 0)
        
        if agent_count >= 10 or depth >= 5:
            return ComplexityLevel.HIGH
        elif agent_count >= 5 or depth >= 3:
            return ComplexityLevel.MEDIUM
        else:
            return ComplexityLevel.LOW
    
    async def calculate_speed_score(
        self,
        execution_time: float,
        complexity_level: ComplexityLevel,
        workflow_type: Optional[str] = None
    ) -> float:
        """Calculate speed score (0.0-1.0) based on execution time vs baseline"""
        
        baseline = await baseline_manager.get_baseline_metrics(complexity_level, workflow_type)
        if not baseline:
            # No baseline available, return neutral score
            return 0.5
        
        # Calculate score using median as target
        target_time = baseline.median_execution_time
        if target_time <= 0:
            return 0.5
        
        # Score calculation: faster = better, with diminishing returns
        ratio = execution_time / target_time
        
        if ratio <= 0.5:  # Exceptionally fast
            return 1.0
        elif ratio <= 0.75:  # Fast
            return 0.9
        elif ratio <= 1.0:  # At baseline
            return 0.75
        elif ratio <= 1.5:  # Slow
            return 0.5
        elif ratio <= 2.0:  # Very slow
            return 0.25
        else:  # Extremely slow
            return 0.1
    
    async def calculate_quality_score(
        self,
        success_rate: float,
        retry_count: int,
        validation_results: Optional[List[Dict]] = None
    ) -> float:
        """Calculate quality score based on success rate, retries, and validation"""
        
        # Base score from success rate
        base_score = success_rate
        
        # Penalty for retries (indicates instability)
        retry_penalty = min(retry_count * 0.1, 0.3)  # Max 30% penalty
        base_score -= retry_penalty
        
        # Bonus/penalty from validation results
        if validation_results:
            validation_score = sum(
                result.get("score", 0.5) for result in validation_results
            ) / len(validation_results)
            # Weight validation at 25% of total score
            base_score = (base_score * 0.75) + (validation_score * 0.25)
        
        return max(0.0, min(1.0, base_score))
    
    def calculate_success_score(
        self,
        agents_succeeded: int,
        agents_failed: int,
        overall_success: bool,
        critical_failures: int = 0
    ) -> float:
        """Calculate success score based on agent completion and overall outcome"""
        
        total_agents = agents_succeeded + agents_failed
        if total_agents == 0:
            return 1.0 if overall_success else 0.0
        
        # Agent-level success rate
        agent_success_rate = agents_succeeded / total_agents
        
        # Overall success bonus/penalty
        overall_bonus = 0.2 if overall_success else -0.3
        
        # Critical failure penalty
        critical_penalty = critical_failures * 0.25
        
        # Calculate final score
        score = agent_success_rate + overall_bonus - critical_penalty
        
        return max(0.0, min(1.0, score))
    
    def calculate_usefulness_score(
        self,
        goal_alignment: float,
        user_feedback: Optional[float] = None,
        business_impact: float = 0.5
    ) -> float:
        """Calculate usefulness score based on goal achievement and impact"""
        
        # Base score from goal alignment
        base_score = goal_alignment
        
        # User feedback component (if available)
        if user_feedback is not None:
            # Weight user feedback at 40% of total
            base_score = (base_score * 0.6) + (user_feedback * 0.4)
        
        # Business impact adjustment
        impact_adjustment = (business_impact - 0.5) * 0.2  # ±10% adjustment
        base_score += impact_adjustment
        
        return max(0.0, min(1.0, base_score))


class BaselineManager:
    """Manages baseline metrics for performance comparison"""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = timedelta(hours=6)
    
    async def get_baseline_metrics(
        self,
        complexity_level: ComplexityLevel,
        workflow_type: Optional[str] = None,
        lookback_days: int = 30
    ) -> Optional[BaselineMetrics]:
        """Get baseline metrics for performance comparison"""
        
        cache_key = f"{complexity_level.value}_{workflow_type}_{lookback_days}"
        
        # Check cache
        if cache_key in self.cache:
            baseline, cached_time = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_ttl:
                return baseline
        
        # Calculate new baseline
        baseline = await self._calculate_baseline(
            complexity_level, workflow_type, lookback_days
        )
        
        # Cache result
        self.cache[cache_key] = (baseline, datetime.now())
        
        return baseline
    
    async def _calculate_baseline(
        self,
        complexity_level: ComplexityLevel,
        workflow_type: Optional[str],
        lookback_days: int
    ) -> Optional[BaselineMetrics]:
        """Calculate baseline metrics from historical data"""
        
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        
        async with db_manager.get_async_session() as session:
            # Build query for historical thought trees
            query = select(ThoughtTree).filter(
                and_(
                    ThoughtTree.completed_at >= cutoff_date,
                    ThoughtTree.status == "completed",
                    ThoughtTree.importance_level == complexity_level.value
                )
            )
            
            # Add workflow type filter if specified
            if workflow_type:
                query = query.filter(
                    ThoughtTree.metadata_["workflow_type"].astext == workflow_type
                )
            
            thought_trees = await session.execute(query.limit(1000))
            thought_trees = thought_trees.scalars().all()
            
            if len(thought_trees) < 5:  # Need minimum sample size
                logger.warning(f"Insufficient data for baseline calculation: {len(thought_trees)} samples")
                return None
            
            # Calculate metrics for each thought tree
            execution_times = []
            success_rates = []
            token_usages = []
            cost_usages = []
            
            for tree in thought_trees:
                if not tree.completed_at or not tree.created_at:
                    continue
                
                # Execution time
                exec_time = (tree.completed_at - tree.created_at).total_seconds()
                execution_times.append(exec_time)
                
                # Success rate from existing score
                success_rates.append(float(tree.success_score or 0.5))
                
                # Get token/cost data from LLM interactions
                llm_interactions = await session.execute(
                    select(LLMInteraction)
                    .filter(LLMInteraction.thought_tree_id == tree.id)
                )
                interactions = llm_interactions.scalars().all()
                
                tree_tokens = sum(
                    (i.token_count_input or 0) + (i.token_count_output or 0)
                    for i in interactions
                )
                tree_cost = sum(i.cost_usd or Decimal('0') for i in interactions)
                
                token_usages.append(tree_tokens)
                cost_usages.append(tree_cost)
            
            # Calculate baseline statistics
            if execution_times:
                avg_exec_time = sum(execution_times) / len(execution_times)
                median_exec_time = sorted(execution_times)[len(execution_times) // 2]
            else:
                avg_exec_time = median_exec_time = 0.0
            
            avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0.5
            avg_token_usage = int(sum(token_usages) / len(token_usages)) if token_usages else 0
            avg_cost = sum(cost_usages) / len(cost_usages) if cost_usages else Decimal('0')
            
            return BaselineMetrics(
                avg_execution_time=avg_exec_time,
                median_execution_time=median_exec_time,
                avg_success_rate=avg_success_rate,
                avg_token_usage=avg_token_usage,
                avg_cost_usd=avg_cost,
                sample_size=len(thought_trees),
                complexity_level=complexity_level,
                last_updated=datetime.now()
            )
    
    async def update_baselines(self) -> None:
        """Update all cached baselines with fresh data"""
        logger.info("Updating baseline metrics cache")
        
        # Clear cache to force recalculation
        self.cache.clear()
        
        # Pre-calculate baselines for common scenarios
        for complexity in ComplexityLevel:
            for workflow_type in [None, "user_prompt", "structured_task", "goal_workflow"]:
                try:
                    await self.get_baseline_metrics(complexity, workflow_type)
                except Exception as e:
                    logger.error(f"Error updating baseline for {complexity.value}/{workflow_type}: {e}")
        
        logger.info("Baseline metrics cache updated")


# Global instances
metrics_calculator = MetricsCalculator()
baseline_manager = BaselineManager()